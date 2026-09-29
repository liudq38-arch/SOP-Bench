import argparse
import gc
import json
import os
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='/data_1/ldq/models/Qwen3-VL-8B-Instruct')
    parser.add_argument('--gpu', default='0')
    parser.add_argument('--frames', type=int, nargs='+', default=[32, 64, 128])
    parser.add_argument('--height', type=int, default=384)
    parser.add_argument('--width', type=int, default=672)
    parser.add_argument('--output', default='reports/design/qwen3vl_profile.jsonl')
    parser.add_argument('--linear-patch', action='store_true')
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    os.environ['HF_HUB_OFFLINE'] = '1'
    import numpy as np
    import torch
    import transformers
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    if not torch.cuda.is_available():
        raise RuntimeError('preflight: CUDA unavailable')
    if args.height % 32 or args.width % 32:
        raise ValueError('preflight: dimensions must be divisible by 32')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in output.read_text().splitlines()] if output.exists() else []
    completed = {(r['frames'], r['height'], r['width']) for r in rows if r.get('status') == 'ok' and r.get('model') == args.model and r.get('linear_patch', False) == args.linear_patch}
    model = Qwen3VLForConditionalGeneration.from_pretrained(args.model, dtype=torch.bfloat16, device_map='cuda:0', attn_implementation='flash_attention_2', local_files_only=True).eval()
    patch_check = None
    if args.linear_patch:
        import types
        layer = model.model.visual.patch_embed
        def linear_forward(self, hidden_states):
            values = hidden_states.to(self.proj.weight.dtype)
            values = values.reshape(-1, self.in_channels * self.temporal_patch_size * self.patch_size * self.patch_size)
            return torch.nn.functional.linear(values, self.proj.weight.reshape(self.embed_dim, -1), self.proj.bias)
        torch.manual_seed(0)
        example = torch.randn(16, layer.in_channels * layer.temporal_patch_size * layer.patch_size ** 2, device='cuda:0', dtype=torch.bfloat16)
        with torch.inference_mode():
            reference = layer(example)
            alternative = linear_forward(layer, example)
        patch_check = {'max_abs_error': float((reference - alternative).abs().max()), 'rtol': .02, 'atol': .02}
        torch.testing.assert_close(reference, alternative, rtol=.02, atol=.02)
        layer.forward = types.MethodType(linear_forward, layer)
        del example, reference, alternative
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    messages = [{'role': 'user', 'content': [{'type': 'video'}, {'type': 'text', 'text': 'Briefly describe the visible content.'}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    base = {'model': args.model, 'torch': torch.__version__, 'transformers': transformers.__version__, 'gpu': torch.cuda.get_device_name(0), 'gpu_total_bytes': torch.cuda.get_device_properties(0).total_memory, 'dtype': 'bfloat16', 'attention': 'flash_attention_2', 'batch': 1, 'max_new_tokens': 32, 'synthetic': True, 'resizing': False, 'linear_patch': args.linear_patch, 'patch_check': patch_check}
    print(json.dumps(base), flush=True)
    for frames in args.frames:
        if (frames, args.height, args.width) in completed:
            continue
        row = dict(base, frames=frames, height=args.height, width=args.width)
        inputs = generated = video = None
        try:
            video = np.random.default_rng(0).integers(0, 256, size=(frames, args.height, args.width, 3), dtype=np.uint8)
            metadata = {'fps': 2.0, 'total_num_frames': frames, 'frames_indices': list(range(frames))}
            inputs = processor(text=[text], videos=[video], video_metadata=[metadata], do_resize=False, do_sample_frames=False, return_tensors='pt')
            row['input_tokens'] = int(inputs.input_ids.shape[-1])
            row['video_grid_thw'] = inputs.video_grid_thw.tolist()
            row['visual_tokens'] = int(inputs.video_grid_thw.prod(dim=-1).sum().item() // 4)
            inputs = inputs.to('cuda:0')
            inputs['pixel_values_videos'] = inputs['pixel_values_videos'].to(torch.bfloat16)
            torch.cuda.synchronize()
            row['allocated_before_bytes'] = torch.cuda.memory_allocated()
            torch.cuda.reset_peak_memory_stats()
            start = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=32, do_sample=False)
            torch.cuda.synchronize()
            row['seconds'] = time.perf_counter() - start
            row['generated_tokens'] = int(generated.shape[-1] - inputs.input_ids.shape[-1])
            row['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
            row['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
            row['status'] = 'ok'
        except Exception as exc:
            row['status'] = 'error'
            row['error'] = f'profile_pipeline: {type(exc).__name__}: {exc}'
        with output.open('a') as handle:
            handle.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)
        del inputs, generated, video
        gc.collect()
        torch.cuda.empty_cache()
        if row['status'] != 'ok':
            break


if __name__ == '__main__':
    main()
