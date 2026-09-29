import base64
from pathlib import Path
import subprocess
import sys
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from impact_qa.common import save_json,read_jsonl
from impact_qa.front_mcq_guidance import guidance_payload


def main():
    out=ROOT/'outputs/impact_qa/front_mcq_expansion_v1/guidance_browser'
    out.mkdir(parents=True,exist_ok=True)
    profile=Path('/home/ldq/snap/firefox/common/codex-timeline-profiles')
    profile.mkdir(parents=True,exist_ok=True)
    log=(out/'geckodriver.log').open('w')
    process=subprocess.Popen(['geckodriver','--host','127.0.0.1','--port','4445','--profile-root',str(profile)],stdout=log,stderr=subprocess.STDOUT)
    client=httpx.Client(base_url='http://127.0.0.1:4445',timeout=90,trust_env=False)
    session=None
    def call(method,path,payload=None):
        response=client.request(method,path,json=payload)
        if response.is_error:raise RuntimeError(response.text)
        response.raise_for_status()
        data=response.json()['value']
        if isinstance(data,dict) and data.get('error'):raise RuntimeError(str(data))
        return data
    try:
        for _ in range(20):
            try:call('GET','/status');break
            except httpx.HTTPError:time.sleep(.5)
        data=call('POST','/session',{'capabilities':{'alwaysMatch':{'browserName':'firefox','moz:firefoxOptions':{'args':['-headless'],'prefs':{'media.autoplay.default':0,'media.autoplay.blocking_policy':0}}}}})
        session=data['sessionId'];prefix='/session/'+session
        def execute(script,*args):return call('POST',prefix+'/execute/sync',{'script':script,'args':list(args)})
        def wait(script,timeout=60):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                result=execute(script)
                if result:return result
                time.sleep(.5)
            (out/'failure_dom.html').write_text(execute('return document.documentElement.outerHTML;'))
            print('client_errors',execute('return window.testErrors;'),flush=True)
            raise TimeoutError('timeline_browser:'+script)
        def screenshot(name):
            (out/name).write_bytes(base64.b64decode(call('GET',prefix+'/screenshot')))
        def element(selector):
            return call('POST',prefix+'/element',{'using':'css selector','value':selector})['element-6066-11e4-a52e-4f735466cecf']
        def click(selector):call('POST',prefix+'/element/'+element(selector)+'/click',{})
        def choose_group(gid):
            button=call('POST',prefix+'/element',{'using':'xpath','value':'//button[contains(.,"筛选与选择视频")]'})['element-6066-11e4-a52e-4f735466cecf']
            call('POST',prefix+'/element/'+button+'/click',{})
            control=element('input[aria-label="Clip：长短目标交错展示"]')
            call('POST',prefix+'/element/'+control+'/click',{})
            execute("const e=document.querySelector('input[aria-label=\"Clip：长短目标交错展示\"]');e.value=arguments[0];e.dispatchEvent(new Event('input',{bubbles:true}));",gid[-6:])
            wait("return [...document.querySelectorAll('[role=option]')].some(e=>e.textContent.includes("+repr(gid[-6:])+"));",10)
            option=call('POST',prefix+'/element',{'using':'xpath','value':'//*[@role="option" and contains(.,"'+gid[-6:]+'")]'})['element-6066-11e4-a52e-4f735466cecf']
            call('POST',prefix+'/element/'+option+'/click',{})
            wait("const r=document.querySelector('.mcq-timeline');return r?.dataset.group==="+repr(gid)+" && r.dataset.state!=='loading';",60)
            call('POST',prefix+'/element/'+button+'/click',{})
        def check_guidance():
            value=execute("const r=document.querySelector('.mcq-guide'),v=document.querySelector('#front-review-video video');return {data:JSON.parse(r.dataset.guide),time:v.currentTime,left:r.querySelector('.guide-left').textContent,right:r.querySelector('.guide-right').textContent,step:r.querySelector('.guide-step').textContent,state:r.querySelector('.guide-state').textContent,full:r.querySelector('.guide-full-state').textContent,expected:r.querySelector('.guide-expected').textContent};")
            payload=value['data'];t=value['time']
            for hand in ['left','right']:
                rows=[r for r in payload['actions'] if r['hand']==hand and r['start']<=t<r['end']]
                assert all(r['label'] in value[hand] for r in rows),(hand,value[hand],rows,t)
            assert all(r['label'] in value['step'] for r in payload['steps'] if r['start']<=t<r['end'])
            if not payload['has_asr']:assert '无ASR' in value['state']
            else:
                row=next((r for r in payload['states'] if r['start']<=t<r['end']),None)
                if row:
                    assert all(c['name']+'：'+payload['state_names'][str(row['values'][i])] in value['full'] for i,c in enumerate(payload['components']))
            value.pop('data');return value
        call('POST',prefix+'/window/rect',{'width':1440,'height':1100})
        call('POST',prefix+'/url',{'url':'http://127.0.0.1:7863'})
        execute("window.testErrors=[];window.addEventListener('error',e=>window.testErrors.push(e.message));window.addEventListener('unhandledrejection',e=>window.testErrors.push(String(e.reason)));")
        scope=wait("const r=document.querySelector('.mcq-timeline');const v=document.querySelector('#front-review-video video');return r && window.impactMCQTimeline && v?.readyState>=1 && r.dataset.state!=='loading' ? {...r.dataset, src:v.currentSrc, duration:v.duration} : null;",90)
        choose_group('fg_7b45423f103c63c25184')
        scope=execute("const r=document.querySelector('.mcq-timeline');return {...r.dataset};")
        print('ready',scope,flush=True)
        execute("document.querySelector('#front-review-timeline').scrollIntoView({block:'start'});")
        start,end=float(scope['start']),float(scope['end'])
        def position(t):
            execute("const v=document.querySelector('#front-review-video video');v.pause();v.currentTime=arguments[0];v.dispatchEvent(new Event('timeupdate'));",t)
            time.sleep(.3)
            return execute("return {state:document.querySelector('.mcq-timeline').dataset.state, text:document.querySelector('.mcq-phase').textContent,outline:document.querySelector('#front-review-video').classList.contains('mcq-target-active')};")
        states={}
        states['before']=position(max(0,start-1));assert states['before']['state']=='before' or start==0
        states['start']=position(start);assert states['start']['state']=='inside'
        states['inside']=position((start+end)/2);assert states['inside']['outline']
        guide_b=check_guidance()
        screenshot('inside.png')
        states['end']=position(end);assert states['end']['state']=='after'
        screenshot('after.png')
        execute("window.impactMCQTimeline.playTarget();")
        wait("const v=document.querySelector('#front-review-video video');return !v.paused;")
        execute("document.querySelector('#front-review-video video').pause();")
        current=execute("return document.querySelector('#front-review-video video').currentTime;")
        assert abs(current-start)<2
        execute("window.impactMCQTimeline.showContext();")
        time.sleep(.2)
        execute("document.querySelector('#front-review-video video').pause();")
        context=execute("return document.querySelector('#front-review-video video').currentTime;")
        assert abs(context-max(0,start-3))<2
        execute("const slider=document.querySelector('.mcq-slider');slider.value=arguments[0];slider.dispatchEvent(new Event('input',{bubbles:true}));",(start+end)/2)
        wait("return document.querySelector('.mcq-timeline').dataset.state==='inside';")
        question_element=call('POST',prefix+'/element',{'using':'css selector','value':'input[aria-label="本clip的MCQ题目"]'})
        call('POST',prefix+'/element/'+question_element['element-6066-11e4-a52e-4f735466cecf']+'/click',{})
        wait("return document.querySelectorAll('[role=option]').length>1;",10)
        option=call('POST',prefix+'/element',{'using':'css selector','value':'[role=option][data-index="1"]'})
        call('POST',prefix+'/element/'+option['element-6066-11e4-a52e-4f735466cecf']+'/click',{})
        switched=wait("const r=document.querySelector('.mcq-timeline');return r && r.dataset.question!=="+repr(scope['question'])+" && r.dataset.state!=='loading' ? {...r.dataset} : null;")
        assert switched['group']==scope['group']
        assert (switched['start'],switched['end'])!=(scope['start'],scope['end'])
        new_state=position((float(switched['start'])+float(switched['end']))/2)
        assert new_state['state']=='inside' and new_state['outline']
        guide_switched=check_guidance()
        screenshot('switched.png')
        folder=out.parent
        groups={r['group_id']:r for r in read_jsonl(folder/'groups.jsonl')}
        for q in read_jsonl(folder/'questions.jsonl'):
            if groups[q['group_id']]['model']!='A':continue
            payload=guidance_payload(q,groups[q['group_id']])
            if len(payload['states'])>1 and payload['states'][0]['values']!=payload['states'][1]['values']:break
        else:raise AssertionError('no ASR transition test case')
        choose_group(q['group_id'])
        wait("return JSON.parse(document.querySelector('.mcq-guide').dataset.guide).model==='A';")
        position(payload['states'][0]['start']+.01);guide_a_before=check_guidance()
        position(payload['states'][1]['start']+.01);guide_a_after=check_guidance()
        assert guide_a_before['full']!=guide_a_after['full']
        execute("document.querySelector('#front-review-guidance').scrollIntoView({block:'center'});")
        screenshot('guidance_A.png')
        execute("const details=[...document.querySelectorAll('.mcq-guide>details')].find(e=>e.querySelector('summary').textContent.includes('拆装步骤'));details.open=true;")
        wait("return [...document.querySelectorAll('.mcq-guide details[open] table')].length>0;")
        save_json(out/'verification.json',dict(status='passed',scope=scope,states=states,seek_time=current,context_time=context,slider_seek=True,switched_scope=switched,switched_state=new_state,guidance_B=guide_b,guidance_switched=guide_switched,guidance_A_before=guide_a_before,guidance_A_after=guide_a_after,screenshots=['inside.png','after.png','switched.png','guidance_A.png'],human_review_written=False))
        print('PASS playback boundaries, seek, context, slider, question/video switch, bilingual hand actions, B no-ASR, A live state transition, reference panel',flush=True)
    finally:
        if session:
            try:call('DELETE','/session/'+session)
            except Exception:pass
        client.close();process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill()
        log.close()


if __name__=='__main__':main()
