def interaction_issues(case, observed):
    target=next(h for h in observed['hands'] if h['hand']==case['event']['hand'])
    names=case['event']['action_names']
    interaction=target['interaction']
    issues=[]
    if len(names)==1:
        name=names[0]
        if name.startswith('hand_loosen_') and interaction=='rotating_fastener_with_tool':
            issues.append('GT_finger_action_described_as_tool_use')
        if name=='hand_spin_drive_shaft' and interaction=='holding':
            issues.append('GT_shaft_rotation_described_as_stabilizing')
        if name.startswith('hold_') and interaction=='rotating_fastener_with_tool':
            issues.append('GT_holding_described_as_fastener_rotation')
    if target.get('tool_tip_relation') in ['pointing_away','no_tool'] and target['tool_contact']=='used_for_action':
        issues.append('tool_use_claim_contradicts_visible_tip_relation')
    return issues
