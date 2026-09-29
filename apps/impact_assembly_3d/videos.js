const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
const typeNames={temporal:'时间',spatial:'位置／方向',handling:'操作／控制',wrong_part:'部件选择',wrong_tool:'工具选择',procedural:'步骤'};
const el=(tag,text,className)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
try{
    const response=await fetch('assembly_videos.json');if(!response.ok)throw new Error(`清单请求失败：${response.status}`);
    const data=await response.json();const container=document.getElementById('videos');container.replaceChildren();
    for(const row of data.videos){
        const card=el('article',undefined,'card');card.id=row.model;
        const heading=el('div',undefined,'heading');const title=el('div');title.append(el('h2',`${row.model} 型 · 完整安装`),el('div',`${clock(row.duration_s)} · 异常标注时间并集 ${row.anomaly_union_s.toFixed(2)} 秒（${(row.anomaly_fraction*100).toFixed(2)}%）`,'summary'));
        const download=el('a','打开原片 ↗','download');download.href=row.media_url;download.target='_blank';download.rel='noopener';heading.append(title,download);
        const video=el('video');video.controls=true;video.preload='metadata';video.playsInline=true;video.src=row.media_url;video.poster=row.poster_url;
        const detail=el('div',undefined,'detail');const live=el('div','等待播放 · 原始GT提示','live');detail.append(live,el('div','安装阶段：点击定位至该阶段首次出现','label'));
        const steps=el('div',undefined,'steps');const seek=t=>{video.currentTime=t;video.pause();};
        for(const step of row.steps){const button=el('button',`${clock(step.start_s)} ${step.title}`);button.onclick=()=>seek(step.start_s);steps.append(button);}detail.append(steps);
        detail.append(el('div',`原始异常标注：${row.anomaly_rows} 条 TAS-B，派生 ATR ${row.atr_segments} 段；点击查看`,'label'));
        const anomalies=el('div',undefined,'anomalies');
        for(const event of row.anomalies){const button=el('button',`${event.start_s.toFixed(2)}–${event.end_s.toFixed(2)}s · ${event.hand==='left'?'左手':'右手'} · ${event.types.map(x=>typeNames[x]).join('、')}`);button.onclick=()=>seek(event.start_s);anomalies.append(button);}detail.append(anomalies);
        detail.append(el('p',row.model==='A'?'完整性参考：主要安装阶段齐全，末尾ASR标注17个组件均为已安装。首尾与主要阶段已抽帧复核；不据此保证每次操作或紧固质量完全正确。':'完整性参考：四个主要安装阶段及结束标注齐全，已抽看首尾与主要阶段。B型没有ASR，不能据此确认每个内部紧固件均正确完成。','note'));
        if(row.model==='B')detail.append(el('p','B型原动作标注中出现了lever名称，与当前B部件参考有冲突；本页保留原异常类别，不把该名称当作已核实的部件身份。','note'));
        detail.append(el('div',row.video_id+'.mp4','filename'));
        video.addEventListener('timeupdate',()=>{const active=row.anomalies.filter(e=>video.currentTime>=e.start_s&&video.currentTime<e.end_s);live.classList.toggle('active',active.length>0);live.textContent=`${clock(video.currentTime)} / ${clock(row.duration_s)} · `+(active.length?`处于原异常标注段：${active.map(e=>`${e.hand==='left'?'左手':'右手'} ${e.types.map(x=>typeNames[x]).join('、')}`).join('；')}`:'当前位置无异常标注；不等于已独立核验正确');});
        video.addEventListener('play',()=>{for(const other of document.querySelectorAll('video'))if(other!==video)other.pause();});
        card.append(heading,video,detail);container.append(card);
    }
    if(location.hash)document.getElementById(location.hash.slice(1))?.scrollIntoView();
}catch(error){document.getElementById('videos').textContent='视频清单加载失败：'+error.message;throw error;}
