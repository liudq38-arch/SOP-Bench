from pathlib import Path

import av


def extract_source_frames(video, indices, folder, annotation_fps):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    indices = sorted(set(map(int, indices)))
    if not indices or indices[0] < 0:
        raise ValueError('source_frames:invalid_indices')
    wanted = set(indices)
    records = []
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        rate = float(stream.average_rate)
        origin = float((stream.start_time or 0) * stream.time_base)
        container.seek(max(0, int((origin + indices[0] / rate) / stream.time_base)), stream=stream, backward=True)
        for frame in container.decode(stream):
            pts = float(frame.pts * frame.time_base)
            index = round((pts - origin) * rate)
            if index > indices[-1]:
                break
            if index not in wanted:
                continue
            path = folder / f'f{index:07d}.jpg'
            frame.to_image().save(path, quality=96)
            records.append({'source_frame_index': index, 'frame_id': f'f{index:07d}', 'pts_s': pts, 'annotation_time_s': index / annotation_fps, 'path': str(path)})
    if [r['source_frame_index'] for r in records] != indices:
        raise ValueError('source_frames:missing_or_duplicate_indices:' + str(video))
    return {'frames': records, 'stream_average_rate': rate, 'stream_start_s': origin, 'annotation_fps': annotation_fps}
