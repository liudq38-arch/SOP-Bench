() => {
    let root = null;
    let payload = null;
    let encoded = null;
    const write = (selector, value) => {
        const node = root?.querySelector(selector);
        if (node && node.textContent !== value) node.textContent = value;
    };
    const active = (rows, time) => rows.filter(row => row.start <= time && time < row.end);
    const update = () => {
        const current = document.querySelector('#front-review-guidance .mcq-guide');
        if (current !== root || current?.dataset.guide !== encoded) {
            root = current;
            encoded = root?.dataset.guide;
            payload = root ? JSON.parse(encoded) : null;
        }
        if (!root || !payload) return;
        const video = document.querySelector('#front-review-video video');
        const ready = video?.readyState >= 1 && (video.currentSrc || video.src).includes(payload.group);
        if (!ready) {
            for (const selector of ['.guide-left', '.guide-right', '.guide-step', '.guide-state', '.guide-full-state']) write(selector, '等待当前视频');
            write('.guide-expected', '视频就绪后显示当前步骤的工具与顺序参照。');
            return;
        }
        const time = video.currentTime;
        const actions = active(payload.actions, time);
        for (const hand of ['left', 'right']) {
            const rows = actions.filter(row => row.hand === hand);
            const target = payload.target_hand === hand ? '（本题目标） ' : '';
            write('.guide-' + hand, target + (rows.length ? rows.map(row => `${row.label} · ${row.start.toFixed(2)}–${row.end.toFixed(2)}s`).join('；') : '此刻无覆盖标注'));
        }
        const steps = active(payload.steps, time);
        write('.guide-step', steps.length ? steps.map(row => row.label).join('；') : '此刻无步骤标注');
        const stepKeys = [...new Set(steps.map(row => row.stage).filter(Boolean))];
        const targetKeys = [...new Set(actions.filter(row => row.hand === payload.target_hand).flatMap(row => Object.keys(payload.stages).filter(key => row.noun !== 'gearbox_housing' && payload.stages[key].components.includes(row.noun))))];
        const keys = targetKeys.length ? targetKeys : stepKeys;
        const expected = keys.map(key => payload.stages[key].title + '：' + payload.stages[key].reference);
        write('.guide-expected', expected.length ? expected.join(' ') : '当前步骤未明确；请先核实具体紧固件，再查下方型号参考，不能根据“螺丝”泛称指定改锥。');
        const notices = ['提醒不是异常裁决；检查可见事实与适用要求。'];
        if (targetKeys.length && stepKeys.length && targetKeys.some(key => !stepKeys.includes(key))) notices.push('本题手的动作对象与粗步骤对象不同，可能是协作或标注粒度差异；请先核对对象，工具参照按本题手的对象显示。');
        if (actions.some(row => ['hand_tighten', 'hand_loosen', 'hand_spin', 'thread'].includes(row.verb))) notices.push('徒手：区分预拧、松后旋出、轴的检查与最终紧固；徒手不自动算错。');
        if (actions.some(row => row.action === 'null' || row.verb === 'hold')) notices.push('持握／NULL不等于停滞，结合另一手和实际进展。');
        if (actions.some(row => row.noun === 'screw')) notices.push('当前有泛称螺丝，具体实例须看视频确认。');
        write('.guide-caution', notices.join(' '));
        const states = active(payload.states, time);
        if (!payload.has_asr || !states.length) {
            const missing = payload.has_asr ? '此刻不在ASR标注覆盖范围内，状态未知。' : '本视频无ASR，安装／拆卸完成状态需看视频确认。';
            write('.guide-state', missing);
            write('.guide-full-state', missing);
        } else {
            const values = states[states.length - 1].values;
            const relevant = new Set([...payload.relevant, ...keys.flatMap(key => payload.stages[key].components)]);
            const format = (part, i) => `${part.name}：${payload.state_names[String(values[i])] || '状态未知'}`;
            const rows = payload.components.map((part, i) => ({part, text: format(part, i)}));
            const chosen = rows.filter(row => relevant.has(row.part.key));
            write('.guide-state', chosen.length ? chosen.slice(0, 3).map(row => row.text).join('；') + (chosen.length > 3 ? `；另${chosen.length - 3}项见完整状态` : '') : '暂无可明确对应的当前组件，请展开完整ASR状态。');
            write('.guide-full-state', rows.map(row => row.text).join('\n') + '\nASR标注可错；“已正确安装”不证明扭矩、内部啮合或实际完成已核实。');
        }
    };
    window.impactMCQGuidance = {update, refresh: update};
    update();
}
