from functools import lru_cache
from hashlib import sha256
from html import escape
import json

from impact_qa.common import ANNOTATIONS, ROOT, read_json
from impact_qa.mcq_native import native_trial


REFERENCE_PATH=ROOT/'configs/impact_qa/review_reference_v1.json'
KNOWLEDGE_PATH=ROOT/'prompts/impact_qa/v28r_object_knowledge.json'
REFERENCE=read_json(REFERENCE_PATH)
KNOWLEDGE=read_json(KNOWLEDGE_PATH)
NAMES={r['canonical_name']:r['name_zh'] for r in KNOWLEDGE['component_groups']+KNOWLEDGE['tools']+KNOWLEDGE['components']}
NAMES.update(gearbox_housing_drive_shaft='壳体与传动轴组合体',spin_drive_shaft='传动轴',tool='未指明工具',null='未标明对象')
NAMES.update(screw='螺丝（实例未明）',M4_nut='M4螺母（标注名；位置未定）')
NAMES.update({r['id']:r['meaning_zh'] for r in KNOWLEDGE['annotation_aliases'] if r['id'] not in NAMES})
NAMES.update({r['id']:'螺丝（旧名 '+r['id']+'；实例映射待核）' for r in KNOWLEDGE['legacy_asr_labels']})
VERBS=dict(adjust='调整',align='对准',attach='连接',detach='分离',dismount='拆离',extract='抽出',flip='翻转',hand_spin='徒手转动',hand_loosen='徒手旋松',hand_tighten='徒手旋紧',hold='持握',insert='插入',loosen='旋松',mount='装入',pick_up='拿起',place='放置',remove='取下',seat='使其就位',store='收纳',thread='起扣／旋入螺纹',tighten='拧紧',transfer='转移')
STEPS=dict(start_angle_grinder_assembly='开始拆装任务',unscrew_anti_vibration_handle='旋出侧手柄',store_anti_vibration_handle='收纳侧手柄',remove_locking_lever_assembly='拆卸拨杆组件',store_locking_lever_assembly='收纳拨杆组件',extract_bearing_plate_assembly='拆卸轴承板组件',store_bearing_plate_assembly='收纳轴承板组件',detach_adapter_plate='拆卸适配板',remove_rotor_assembly='拆卸转子轴组件',store_rotor_assembly='收纳转子轴组件',store_gearbox_housing='收纳壳体',store_adapter_plate='收纳适配板',retrieve_gearbox_housing='取用壳体',retrieve_rotor_assembly='取用转子轴组件',install_rotor_assembly='安装转子轴组件',attach_adapter_plate='安装适配板',retrieve_adapter_plate='取用适配板',retrieve_anti_vibration_handle='取用侧手柄',retrieve_bearing_plate_assembly='取用轴承板组件',insert_bearing_plate_assembly='安装轴承板组件',retrieve_locking_lever_assembly='取用拨杆组件',install_locking_lever_assembly='安装拨杆组件',screw_on_anti_vibration_handle='旋入侧手柄',store_tool='收纳工具',finish_angle_grinder_assembly='结束拆装任务',null='未标明步骤（不等于没有工作）')
STATE_NAMES={'-1':'标注装配异常','0':'标注未安装','1':'标注已正确安装'}


def stage_key(action):
    return next((key for key,value in REFERENCE['stages'].items() if any(token in action for token in value['tokens'])),None)


def source_info(path):
    return {'path':str(path.relative_to(ROOT)),'sha256':sha256(path.read_bytes()).hexdigest()}


@lru_cache(maxsize=128)
def state_document(trial_id):
    path=ANNOTATIONS/'ASR/annotations'/(trial_id+'_front_asr.json')
    return (read_json(path),source_info(path)) if path.exists() else (None,None)


def guidance_payload(question,group):
    trial=native_trial(group['trial_id'],'front')
    offset=group['start_frame']/group['fps']
    end=group['end_frame_exclusive']/group['fps']
    actions=[]
    for row in trial['actions']:
        a,b=row['start_frame']/trial['fps'],row['end_frame_exclusive']/trial['fps']
        if a>=end or b<=offset:continue
        label='未标明动作（NULL；不等于空闲）' if row['action']=='null' else VERBS.get(row['verb'],row['verb'])+' · '+NAMES.get(row['noun'],row['noun'])
        actions.append({'start':max(0,a-offset),'end':min(end,b)-offset,'hand':row['hand'],'label':label,'verb':row['verb'],'noun':row['noun'],'action':row['action'],'source':row['source']})
    task_path=ANNOTATIONS/'TAS-S/front'/(group['trial_id']+'_front.json')
    task=read_json(task_path) if task_path.exists() else None
    task_source=source_info(task_path) if task else None
    steps=[]
    if task:
        fps=task['meta_data']['fps']
        for i,row in enumerate(task['segments']):
            a,b=row['f_start']/fps,(row['f_end']+1)/fps
            if a>=end or b<=offset:continue
            steps.append({'start':max(0,a-offset),'end':min(end,b)-offset,'label':STEPS.get(row['label'],row['label']),'stage':stage_key(row['label']),'raw':row['label'],'source':dict(task_source,pointer=f'/segments/{i}')})
    doc,asr_source=state_document(group['trial_id'])
    states=[];components=[]
    if doc:
        components=[{'id':row['id'],'key':row['name'],'name':NAMES.get(row['name'],row['name'])} for row in doc['components']]
        indexed=sorted(enumerate(doc['state_sequence']),key=lambda pair:pair[1]['frame'])
        coverage_end=(doc.get('view_end',doc['frame_count']-1)+1)/doc['fps']
        coverage_start=doc.get('view_start',0)/doc['fps']
        for n,(i,row) in enumerate(indexed):
            a=max(coverage_start,row['frame']/doc['fps'])
            b=min(coverage_end,indexed[n+1][1]['frame']/doc['fps'] if n+1<len(indexed) else coverage_end)
            if a>=end or b<=offset:continue
            states.append({'start':max(0,a-offset),'end':min(end,b)-offset,'values':row['state'],'source':dict(asr_source,pointer=f'/state_sequence/{i}')})
    model=group['model']
    if model not in REFERENCE['workflows']:raise ValueError('front_mcq_guidance:unknown_model:'+str(model))
    a,b=question['scope']['playback_interval_s']
    relevant={row['noun'] for row in actions if row['start']<b and row['end']>a}
    for row in steps:
        if row['start']<b and row['end']>a and row['stage']:
            relevant.update(REFERENCE['stages'][row['stage']]['components'])
    relevant.discard('gearbox_housing_drive_shaft')
    return {'question':question['question_id'],'group':group['group_id'],'model':model,'workflow':group['workflow'],'duration':group['duration_s'],'target_hand':question['scope']['hand'],'actions':actions,'steps':steps,'states':states,'components':components,'state_names':STATE_NAMES,'relevant':sorted(relevant),'has_asr':doc is not None,'stages':{k:{'title':v['title'],'reference':v[model],'components':v['components']} for k,v in REFERENCE['stages'].items()},'sources':{'knowledge':source_info(KNOWLEDGE_PATH),'reference':source_info(REFERENCE_PATH),'TAS-S':task_source,'ASR':asr_source}}


def table(headers,rows):
    head=''.join('<th>'+escape(str(x))+'</th>' for x in headers)
    body=''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)
    return '<div class="guide-table-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def reference_html(model,workflow):
    variant=next(v for v in KNOWLEDGE['model_variants'] if v['marker']==model)
    parts=['<p><b>'+escape(variant['product'])+'</b> · '+escape(variant['reference_zh'])+'</p>']
    parts.append('<p>下表是参考拆装路径；只有必要连接依赖可作为顺序约束。B型尚无已完整核验的逐步手册。</p>')
    for kind,title in [('assemble','安装参考'),('disassemble','拆卸参考')]:
        parts.append('<details'+(' open' if kind==workflow else '')+'><summary>'+title+'</summary>'+table(['操作对象','过程／工具','依据与限制'],REFERENCE['workflows'][model][kind])+'</details>')
    tools=[[r['name_zh'],r['appearance_zh'],r['role_zh']] for r in KNOWLEDGE['tools']]
    parts.append('<details><summary>四种工具：外观与用途（型号适用范围见说明）</summary>'+table(['名称','外观','用途'],tools)+'</details>')
    parts.append('<details><summary>部件名称与作用</summary>'+table(['部件','外观','作用／型号限制'],[[r['name_zh'],r['appearance_zh'],r['role_zh']] for r in KNOWLEDGE['component_groups']])+'</details>')
    parts.append('<details><summary>六类异常定义与排除条件</summary>'+table(['类别','工作定义','审核要点'],[[r['name']+' · '+r['zh'],r['definition'],r['check']] for r in REFERENCE['categories']])+'<p>Correct：在可见性与要求充分的指定范围内，没有发现违反要求；证据不足不能直接选Correct。</p></details>')
    links=' · '.join('<a target="_blank" rel="noopener" href="'+escape(KNOWLEDGE['sources'][k]['url'],quote=True)+'">'+name+'</a>' for k,name in [('paper','论文'),('manual','A型官方手册图'),('official_figure','A/B官方结构图')])
    parts.append('<p class="guide-footnote">'+links+'。参考工具映射不等于当前目标已被确认。</p>')
    return ''.join(parts)


def guidance_html(question,group):
    payload=guidance_payload(question,group)
    data=escape(json.dumps(payload,ensure_ascii=False,separators=(',',':')),quote=True)
    model=group['model'];workflow=group['workflow']
    title=model+'型 · '+('安装' if workflow=='assemble' else '拆卸')
    checks=[]
    evidence={r['category']:r for r in question.get('visual_evidence',[])}
    for row in REFERENCE['categories']:
        if row['id'] not in question['candidate_option_ids']:continue
        review=evidence.get({'B':'temporal','C':'spatial','D':'handling','E':'wrong_part','F':'wrong_tool','G':'procedural'}[row['id']],{})
        status={'supported':'模型有支持，待人审','contradicted':'模型提出反证','insufficient':'模型证据不足'}.get(review.get('verdict'),'待核验')
        checks.append('<li><b>'+escape(row['name'])+'</b> · '+status+'：'+escape(row['check'])+'</li>')
    refs=reference_html(model,workflow)
    return f'''<section class="mcq-guide" data-guide="{data}" data-question="{escape(question['question_id'])}">
<div class="guide-heading"><strong>拆装辅助 · {title}</strong><span>随播放更新 · 标注参考</span></div>
<div class="guide-hands"><div><b>左手</b><span class="guide-left">等待视频</span></div><div><b>右手</b><span class="guide-right">等待视频</span></div></div>
<p><b>当前步骤</b> <span class="guide-step">等待视频</span></p>
<p><b>组件状态</b> <span class="guide-state">等待视频</span></p>
<p class="guide-reference"><b>该组件的工具／顺序参照</b> <span class="guide-expected">确认具体部件和阶段后查看。</span></p>
<p class="guide-caution">标注可错；以下为核验提醒，不自动认定视频操作错误。</p>
<details><summary>本题异常核验要点（{len(checks)}类候选）</summary><ul>{''.join(checks)}</ul></details>
<details><summary>当前完整组件状态（ASR）</summary><div class="guide-full-state">等待视频</div></details>
<details><summary>{model}型拆装步骤、工具、部件与六类定义</summary>{refs}</details>
<p class="guide-footnote">动作：TAS-B · 步骤：TAS-S · 状态：ASR。工具参照仅用于相应紧固操作，不要求取放／持握时用工具；缺失标注显示未知。</p>
</section>'''
