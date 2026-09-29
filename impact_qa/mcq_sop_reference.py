from impact_qa.common import ANNOTATIONS, ROOT, read_json
from impact_qa.v26_data import digest


def make_sop(model, workflow):
    assembly = workflow == 'assemble'
    prefix = model + ('_I' if assembly else '_D')
    steps = []
    def add(key, title, parts, tools, expected, phase, certainty='documented', unknown=None):
        steps.append(dict(id=f'{prefix}_{key}', number=len(steps)+1, title=title, expected_parts=parts.split('|'), expected_tools=tools.split('|'), expected=expected, tas_s_phase=phase, requirement_certainty=certainty, unknown=unknown or []))
    if assembly:
        add('ROTOR','转子轴组件对位入壳','gearbox_housing|drive_shaft','hands','轴端进入壳体通道，支撑、对位和必要的转动检查允许。','install_rotor_assembly')
        add('GEAR','小锥齿轮就位','drive_shaft|bevel_gear','hands','小锥齿轮安装在匹配轴端，不能与轴承板背面大齿轮混同。','install_rotor_assembly')
        add('NUT','内部保持螺母','drive_shaft|bevel_gear|internal_retaining_nut','hands|combination_wrench','螺母先手指就位再用匹配扳手；预拧与支撑轴允许。','install_rotor_assembly','manual_A' if model=='A' else 'interface_inference_B',['M4/M6动作名称冲突；B止转方法及扳手规格未知。'])
        if model == 'A':
            add('ADAPTER','适配板对位','adapter_plate|gearbox_housing|drive_shaft','hands','适配板在转子入壳端就位。','attach_adapter_plate')
            for n in ['1','2']:
                add('ADAPTER_FIX'+n,'适配板紧固连接'+n,'adapter_plate|gearbox_housing|adapter_screw|M4_nut','hands|phillips_screwdriver','对应长螺丝与M4螺母配合，红黄十字操作螺丝端；允许预拧。','attach_adapter_plate')
        else:
            for n in ['1','2']:
                add('HOUSING_FIX'+n,'壳体与轴组件支承连接'+n,'gearbox_housing|drive_shaft|housing_screw','hands|phillips_screwdriver','图示螺丝连接壳体与轴组件法兰；红黄十字由局部样例支持，须核对实际槽口。','install_rotor_assembly','diagram_and_local_example',['不是A的适配板螺丝/M4配对结构；具体螺丝长度与批头规格未定。'])
            add('ADAPTER','转子远端适配板','adapter_plate|drive_shaft','hands','图示适配板在转子远端对位。','attach_adapter_plate','diagram_position_only',['确切保持方式及压装/卡扣未核验，不凭此判工具或连接异常。'])
        add('BEARING','轴承板组件对位','bearing_plate|gearbox_housing','hands','板的输出轴朝外、背面传动件朝齿轮腔，对位后再紧固。','insert_bearing_plate_assembly')
        for n in ['1','2']:
            add('BEARING_FIX'+n,'轴承板螺丝'+n,'bearing_plate|gearbox_housing|bearing_screw','hands|'+('torx_screwdriver' if model=='A' else 'flat_head_screwdriver'), '对应两颗轴承板螺丝中的一颗。'+('A手册使用绿黑Torx六瓣梅花。' if model=='A' else 'B拆卸样例使用黑蓝一字，非排他规范，实际槽口优先。'),'insert_bearing_plate_assembly','manual_A' if model=='A' else 'local_example_not_exclusive',['B轴承板槽口具体形状/可适配批头不能从样例反推唯一要求。'] if model=='B' else [])
        if model=='A':
            add('LEVER','拨杆组件对位','lever|spring|washer|bearing_plate','hands','核对拨杆、弹簧、垫圈配套并支撑。','install_locking_lever_assembly','manual_A',['弹簧/垫圈精确叠放未确认，不能按猜测叠放判错。'])
            add('LEVER_FIX','拨杆螺丝紧固','lever|spring|washer|screw_lever','hands|torx_screwdriver','用绿黑Torx操作拨杆螺丝，允许手指预拧。','install_locking_lever_assembly')
        add('HANDLE','侧手柄旋入','anti_vibration_handle|gearbox_housing','hands','自身螺纹柱旋入壳体侧孔，徒手旋转合法。','screw_on_anti_vibration_handle')
        add('CHECK','装配状态检查','assembled_device','hands','核对连接终态；检查/必要对位不视作无效动作。','finish_angle_grinder_assembly')
    else:
        add('HANDLE','旋出侧手柄','anti_vibration_handle|gearbox_housing','hands','扶稳并旋出手柄自身螺纹柱。','unscrew_anti_vibration_handle')
        if model=='A':
            add('LEVER_FIX','解除拨杆螺丝','screw_lever|lever|spring|washer','hands|torx_screwdriver','绿黑Torx松开拨杆螺丝，控制小件。','remove_locking_lever_assembly')
            add('LEVER','取下拨杆小组件','lever|spring|washer|screw_lever','hands','紧固解除后取下并保管小件，不指定未经核实的叠放。','remove_locking_lever_assembly','manual_A',['精确叠放未知。'])
        for n in ['1','2']:
            add('BEARING_FIX'+n,'解除轴承板螺丝'+n,'bearing_plate|gearbox_housing|bearing_screw','hands|'+('torx_screwdriver' if model=='A' else 'flat_head_screwdriver'),'解除对应连接，松后徒手旋出合法；'+('A绿黑Torx。' if model=='A' else 'B黑蓝一字为观察样例，槽口优先。'),'extract_bearing_plate_assembly','manual_A' if model=='A' else 'local_example_not_exclusive')
        add('BEARING','取下轴承板','bearing_plate|gearbox_housing','hands','两处连接解除后移出板组件，使内部可接近。','extract_bearing_plate_assembly')
        if model=='A':
            for n in ['1','2']:
                add('ADAPTER_FIX'+n,'解除适配板连接'+n,'adapter_plate|gearbox_housing|adapter_screw|M4_nut','hands|phillips_screwdriver','红黄十字松长螺丝并保管配套M4螺母；可手指旋出已松螺丝。','detach_adapter_plate')
        else:
            add('ADAPTER','分离远端适配板','adapter_plate|drive_shaft','hands','按真实保持方式分离转子远端适配板。','detach_adapter_plate','diagram_position_only',['精确保持方式和与其他步骤的依赖未确认。'])
            for n in ['1','2']:
                add('HOUSING_FIX'+n,'解除壳体连接螺丝'+n,'gearbox_housing|drive_shaft|housing_screw','hands|phillips_screwdriver','解除壳体与轴支承法兰连接；十字为局部样例，匹配实际槽口。','detach_adapter_plate','diagram_and_local_example')
        add('NUT','松开内部保持螺母','drive_shaft|bevel_gear|internal_retaining_nut','hands|combination_wrench','内部可接近后解除螺母保持；松后手指旋出允许。','remove_rotor_assembly','manual_A' if model=='A' else 'interface_inference_B',['M4/M6命名冲突，B扳手规格与止转方法未核验。'])
        add('GEAR','取下小锥齿轮','drive_shaft|bevel_gear','hands','保持螺母解除后分离轴端小锥齿轮。','remove_rotor_assembly')
        add('ROTOR','分离轴组件和壳体','drive_shaft|gearbox_housing','hands','相关保持连接解除后支撑并分离轴组件。','remove_rotor_assembly')
        if model=='A':
            add('ADAPTER','整理适配板','adapter_plate|drive_shaft|gearbox_housing','hands','相关阻挡连接解除后分离与归置适配板。','detach_adapter_plate','manual_A',['确切取下时点可随实际连接解除而不同。'])
        add('CHECK','归置和检查','all_removed_parts|tools','hands','有已知工位规则才判断放置违规；暂放桌面不自动错误。','finish_angle_grinder_assembly','reference',['确切料盒位置/朝向规则未知。'])
    ids={s['id'].removeprefix(prefix+'_'):s['id'] for s in steps}
    edges=[]
    def edge(before,after,why):
        edges.append(dict(before=ids[before],after=ids[after],requirement=why,provenance='component_connection_requirement',applicability='只有相关操作/连接身份在图像中确认，才能用于当前目标'))
    if assembly:
        edge('GEAR','NUT','齿轮就位后才完成其保持螺母紧固。')
        for i in ['1','2']:
            edge('BEARING','BEARING_FIX'+i,'板先对位再完成该固定点紧固；预穿螺丝不等于完成紧固。')
            edge('ADAPTER' if model=='A' else 'ROTOR',('ADAPTER_FIX' if model=='A' else 'HOUSING_FIX')+i,'相应连接件先对位再完成紧固。')
        if model=='A':edge('LEVER','LEVER_FIX','小组件就位后完成拨杆紧固。')
    else:
        for i in ['1','2']:
            edge('BEARING_FIX'+i,'BEARING','取下板前必须解除该固定连接。')
            edge(('ADAPTER_FIX' if model=='A' else 'HOUSING_FIX')+i,'ROTOR','分离轴组件/壳体前必须解除仍约束二者的该连接。')
        edge('NUT','GEAR','轴端保持螺母解除后取齿轮。')
        edge('GEAR','ROTOR','小齿轮仍在腔内形成阻挡时，先解除再分离轴组件。')
        if model=='A':edge('LEVER_FIX','LEVER','取下小组件前解除拨杆紧固。')
    swap=[dict(steps=[ids['BEARING_FIX1'],ids['BEARING_FIX2']],condition='两颗对应螺丝的先后可交换；遵守对位或解除后分离的共同前置。'),dict(steps=[ids['HANDLE'],ids['ROTOR']],condition='侧手柄与内部操作可换序，只要不妨碍支撑和实际可接近性。'),dict(steps=[ids[('ADAPTER_FIX' if model=='A' else 'HOUSING_FIX')+'1'],ids[('ADAPTER_FIX' if model=='A' else 'HOUSING_FIX')+'2']],condition='两处对应连接操作先后可交换。')]
    tools=[dict(name=t['canonical_name'],appearance=t['appearance_zh']) for t in read_json(ROOT/'configs/impact_qa/object_knowledge_v2.json')['tools']]
    return dict(model=model,workflow=workflow,steps=steps,hard_prerequisites=edges,interchangeable_step_groups=swap,order_policy='编号是参考组织，不是完整刚性全序；未列硬边不代表已知必须先后。图像中未见历史前置状态不能推断前置未完成。',tools=tools,parts_scope='A按手册；B官方图未单列A拨杆/弹簧/垫圈或适配板M4螺母对，但这不是证明每个B样本绝无这些件。',handling_scope='每步清单描述当前操作对象，不禁止合理预取、转交、归置或另一手并行操作。确认与当前任务无关且排除合法准备/协作后才能判多余。',unknowns=['实际螺丝槽口/规格/扭矩与装配公差','工位/料盒的唯一位置和朝向规则','仅凭静态抽帧无法确认长间隔内没有状态推进'],source_policy='步骤由手册/部件图重建，PSR仅校核组件词表，不是PSR官方偏序图。')


def build_reference():
    psr=read_json(ANNOTATIONS/'PSR/labels/procedure_info_IMPACT.json')
    names=read_json(ANNOTATIONS/'PSR/labels/component_names.json')
    sources=[ANNOTATIONS/'PSR/labels/procedure_info_IMPACT.json',ANNOTATIONS/'PSR/labels/component_names.json',ROOT/'sources/impact_docs/Manual_Book.svg',ROOT/'sources/impact_docs/2anglegrinderconfig.svg',ROOT/'configs/impact_qa/object_knowledge_v2.json',ROOT/'reports/impact_qa/assembly_disassembly_AB_bilingual.md']
    return dict(version='v1',source_sha256={str(p.relative_to(ROOT)):digest(str(p)) for p in sources},psr_audit=dict(entries=len(psr),components=len(names),all_expected_flags_false=all(not r[k] for r in psr for k in ['expected_in_assy','expected_before_subgoal','expected_in_main']),dependency_edges_provided=False,component_names=names),procedures={m+'_'+w:make_sop(m,w) for m in ['A','B'] for w in ['assemble','disassemble']})
