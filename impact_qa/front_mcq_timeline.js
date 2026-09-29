() => {
    if (window.impactMCQTimeline) {
        window.impactMCQTimeline.refresh();
        return;
    }
    let binding = null;
    let scheduled = false;
    const events = ['timeupdate', 'seeking', 'seeked', 'loadedmetadata', 'durationchange', 'emptied', 'play', 'pause'];
    const text = (node, value) => {
        if (node && node.textContent !== value) node.textContent = value;
    };
    const phase = (time, start, end) => time < start ? 'before' : time < end ? 'inside' : 'after';
    const ready = b => b && b.video.readyState >= 1 && (b.video.currentSrc || b.video.src).includes(b.root.dataset.group);
    const update = () => {
        const b = binding;
        if (!b) return;
        const loaded = ready(b);
        const time = loaded ? Math.max(0, Math.min(b.duration, b.video.currentTime || 0)) : 0;
        const state = loaded ? phase(time, b.start, b.end) : 'loading';
        if (b.root.dataset.state !== state) b.root.dataset.state = state;
        const labels = {before: '区间前 · 上下文', inside: '正在判断区间内', after: '区间后 · 上下文', loading: '等待当前视频'};
        text(b.root.querySelector('.mcq-phase'), labels[state]);
        text(b.root.querySelector('.mcq-current-time'), `当前 ${time.toFixed(2)}秒 / ${b.duration.toFixed(2)}秒`);
        b.root.querySelector('.mcq-playhead').style.left = `${time / b.duration * 100}%`;
        b.slider.value = String(time);
        b.slider.disabled = !loaded;
        b.slider.setAttribute('aria-valuetext', `${time.toFixed(2)}秒，${labels[state]}`);
        b.host.classList.toggle('mcq-target-active', state === 'inside');
        b.video.setAttribute('aria-description', `本题判断区间 ${b.start.toFixed(2)}至${b.end.toFixed(2)}秒`);
        window.impactMCQGuidance?.update();
    };
    const seek = (seconds, play = false) => {
        const b = binding;
        if (!ready(b)) return false;
        b.video.currentTime = Math.max(0, Math.min(seconds, b.duration, b.video.duration));
        update();
        if (play) b.video.play().catch(() => {});
        return true;
    };
    const clear = () => {
        if (!binding) return;
        for (const event of events) binding.video.removeEventListener(event, update);
        binding.slider.removeEventListener('input', binding.input);
        binding.host.classList.remove('mcq-target-active');
        binding.video.removeAttribute('aria-description');
        binding = null;
    };
    const refresh = () => {
        const root = document.querySelector('#front-review-timeline .mcq-timeline');
        const host = document.querySelector('#front-review-video');
        const video = host?.querySelector('video');
        if (!root || !video) {
            clear();
            return;
        }
        const key = [root.dataset.question, root.dataset.group, root.dataset.start, root.dataset.end].join('|');
        if (binding?.root === root && binding?.video === video && binding.key === key) {
            window.impactMCQGuidance?.refresh();
            return;
        }
        clear();
        const start = Number(root.dataset.start), end = Number(root.dataset.end), duration = Number(root.dataset.duration);
        const slider = root.querySelector('.mcq-slider');
        if (![start, end, duration].every(Number.isFinite) || !(0 <= start && start < end && end <= duration + 0.000001) || !slider) return;
        const input = () => seek(Number(slider.value));
        binding = {root, host, video, slider, key, start, end, duration, input};
        for (const event of events) video.addEventListener(event, update);
        slider.addEventListener('input', input);
        update();
    };
    const observer = new MutationObserver(() => {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => { scheduled = false; refresh(); });
    });
    observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['src', 'data-question', 'data-start', 'data-end', 'data-group', 'data-guide']});
    window.impactMCQTimeline = {
        refresh,
        phase,
        playTarget: () => { refresh(); return binding ? seek(binding.start, true) : false; },
        showContext: () => { refresh(); return binding ? seek(Math.max(0, binding.start - 3), true) : false; }
    };
    refresh();
}
