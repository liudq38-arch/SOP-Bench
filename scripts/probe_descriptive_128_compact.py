import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from impact_qa.common import read_json, save_json
from impact_qa.descriptive_v21 import FOLDER, ClientPool


async def main():
    item = next(x for x in read_json(FOLDER / 'long_probe_inputs.json') if x['name'] == 'first_128')
    pool = ClientPool()
    result = {'status': 'error', 'video': item['video'], 'change': 'At most four evidence frames per event and event-specific time bounds; same 128 video frames and output budget.'}
    try:
        response = await pool.call('observe_video', item['payload'], item['video']['sampled_frames'], video=item['video'], suffix='first_128_compact_citations', prompt_extra='Return at most six distinct visible events. Use two to four specific citation frames per event, never copy the entire sampled-frame manifest into an event. Assign each event bounds to the actual supporting observations for that event; a short pickup must not automatically inherit the whole video interval. Separate actual before/after states. If onset/offset cannot be resolved, state that uncertainty. Avoid asserting a screw turns when only the hand/tool motion is visible. A precise event boundary cannot be invented merely to satisfy this instruction.')
        result.update(status='ok', result=response['result'], usage=response['usage'], seconds=response['seconds'], cache_key=response['cache_key'])
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        await pool.close()
        save_json(FOLDER / 'long_probe_128_compact.json', result)
        print(json.dumps({k: result.get(k) for k in ['status', 'usage', 'seconds', 'error']}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
