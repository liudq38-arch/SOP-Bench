import * as THREE from 'three';
import {OrbitControls} from 'three/addons/OrbitControls.js';
import {buildModelB,stepsB,removeTitlesB,removeDescriptionsB} from './model_b.js?v=2';

const $=id=>document.getElementById(id);
const viewport=$('viewport');
const scene=new THREE.Scene();
scene.fog=new THREE.FogExp2(0x141c27,.025);
const camera=new THREE.PerspectiveCamera(38,1,.05,100);
let renderer;
try {renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});}
catch(error){$('loading').innerHTML='当前浏览器未启用 WebGL。请开启硬件加速，或换用支持 WebGL 的浏览器。';throw error;}
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.35;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
viewport.prepend(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;controls.dampingFactor=.09;controls.minDistance=3;controls.maxDistance=22;controls.maxPolarAngle=Math.PI*.94;
scene.add(new THREE.HemisphereLight(0xd9edff,0x283b49,2.4));
const light=new THREE.DirectionalLight(0xffecd0,3.8);light.position.set(1,9,6);light.castShadow=true;light.shadow.mapSize.set(2048,2048);light.shadow.camera.left=-9;light.shadow.camera.right=9;light.shadow.camera.top=9;light.shadow.camera.bottom=-9;scene.add(light);
const rim=new THREE.DirectionalLight(0x7fb9eb,2.2);rim.position.set(-6,4,-3);scene.add(rim);
const fill=new THREE.DirectionalLight(0xfde3be,1.3);fill.position.set(5,2,1);scene.add(fill);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:0x17232e,roughness:.92}));floor.rotation.x=-Math.PI/2;floor.position.y=.18;floor.receiveShadow=true;scene.add(floor);
const grid=new THREE.GridHelper(24,48,0x344c5d,0x223746);grid.position.y=.19;grid.material.transparent=true;grid.material.opacity=.3;scene.add(grid);
const root=new THREE.Group();scene.add(root);
let parts=new Map();
const materials={metal:0x98adbb,dark:0x25313c,black:0x181e24,gear:0xc4ba98,rotor:0x788a90,copper:0xc78d60};
function material(color,metalness=.65,roughness=.32){return new THREE.MeshStandardMaterial({color,metalness,roughness});}
function mesh(geometry,color,metalness=.65){const m=new THREE.Mesh(geometry,material(color,metalness));m.castShadow=true;m.receiveShadow=true;return m;}
function box(group,size,pos,color){const m=mesh(new THREE.BoxGeometry(...size),color);m.position.set(...pos);group.add(m);return m;}
function cylinder(group,r1,r2,length,pos,color,axis='z',sides=48){const m=mesh(new THREE.CylinderGeometry(r1,r2,length,sides),color);if(axis==='z')m.rotation.x=Math.PI/2;else if(axis==='x')m.rotation.z=Math.PI/2;m.position.set(...pos);group.add(m);return m;}
function ring(group,outer,inner,depth,pos,color,axis='z',sides=64){const shape=new THREE.Shape();shape.absarc(0,0,outer,0,Math.PI*2,false);const hole=new THREE.Path();hole.absarc(0,0,inner,0,Math.PI*2,true);shape.holes.push(hole);const m=mesh(new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.012,bevelThickness:.012,curveSegments:sides}),color);m.geometry.translate(0,0,-depth/2);if(axis==='x')m.rotation.y=Math.PI/2;else if(axis==='y')m.rotation.x=-Math.PI/2;m.position.set(...pos);group.add(m);return m;}
function gear(group,radius,depth,pos,color,axis='z'){const g=new THREE.Group();ring(g,radius*.84,.11,depth,[0,0,0],color);for(let i=0;i<22;i++){const a=i*Math.PI*2/22;const tooth=box(g,[radius*.15,radius*.2,depth],[Math.cos(a)*radius*.88,Math.sin(a)*radius*.88,0],color);tooth.rotation.z=a-Math.PI/2;}if(axis==='x')g.rotation.y=Math.PI/2;g.position.set(...pos);group.add(g);return g;}
function add(id,name,assembled,exploded,step,build,note,axis='z'){
    const g=new THREE.Group();build(g);root.add(g);
    const label=document.createElement('span');label.className='part-label';label.textContent=name;$('labels').append(label);
    const part={id,name,g,assembled:new THREE.Vector3(...assembled),exploded:new THREE.Vector3(...exploded),step,note,axis,label,baseQ:g.quaternion.clone(),meshes:[]};
    g.traverse(node=>{if(node.isMesh){node.userData.part=id;part.meshes.push(node);}});parts.set(id,part);return part;
}
function screw(group,type='torx',length=.5){cylinder(group,.044,.044,length,[0,0,-length/2],materials.metal);cylinder(group,.1,.105,.07,[0,0,.015],materials.metal);for(let i=0;i<7;i++)ring(group,.047,.038,.012,[0,0,-i*length/8-.045],0x63727b);const cut=0x17212b;if(type==='phillips'){box(group,[.12,.025,.009],[0,0,.055],cut);box(group,[.025,.12,.009],[0,0,.055],cut);}else if(type==='flat')box(group,[.14,.025,.009],[0,0,.055],cut);else for(let i=0;i<6;i++){const a=i*Math.PI/3;cylinder(group,.021,.021,.012,[Math.cos(a)*.027,Math.sin(a)*.027,.055],cut);}}
function nut(group){ring(group,.14,.053,.12,[0,0,0],materials.metal,'z',6);}
const housing=add('housing','齿轮箱壳体',[0,2.2,0],[0,2.2,0],0,g=>{
    ring(g,.95,.77,.65,[0,0,0],materials.dark);ring(g,.92,.57,.12,[0,0,-.36],materials.dark);ring(g,1,.76,.1,[0,0,.36],materials.metal);
    box(g,[1.5,.2,.65],[0,-.8,0],materials.dark);ring(g,.43,.28,.6,[-.95,0,0],materials.dark,'x');
    ring(g,.23,.11,.35,[.91,0,.02],materials.dark,'x');
},'装配主体，连接传动轴、轴承板及侧手柄。当前壳体为简化开口模型。');
add('rotor','传动轴 / 转子',[-2.03,2.2,0],[-4.55,1.6,-.2],1,g=>{
    cylinder(g,.08,.08,3.6,[.28,0,0],materials.metal,'x');cylinder(g,.3,.3,1.55,[-.2,0,0],materials.rotor,'x');cylinder(g,.46,.46,.15,[.8,0,0],0xc4cdc0,'x');
    for(let i=0;i<14;i++){const a=i*Math.PI/7;const fin=box(g,[.14,.035,.23],[.8,Math.cos(a)*.32,Math.sin(a)*.32],0xc9d1c7);fin.rotation.x=a;}
    cylinder(g,.18,.18,.26,[-1.1,0,0],materials.copper,'x');
},'传动轴不是轴承板上伸出的输出轴；长轴、风扇轮与转子合并为一个组件。','x');
add('pinion','小锥齿轮',[-.13,2.2,0],[-.4,4.65,-.2],2,g=>gear(g,.29,.22,[0,0,0],materials.gear,'x'),'齿形被简化，仅表示轴端小齿轮；不模拟真实锥齿啮合。','x');
add('shaftNut','内部保持螺母',[.14,2.2,0],[1.05,4.55,0],3,g=>{nut(g);g.rotation.y=Math.PI/2;},'保持轴端小齿轮。官方图为M6，部分动作标注为M4；此处不据图形确定规格。','x');
add('adapter','适配板',[-1.29,2.2,0],[-3.15,3.7,.4],4,g=>{ring(g,.67,.49,.19,[0,0,0],0x263842,'x');for(const y of [-.52,.52])box(g,[.22,.22,.25],[0,y,0],0x344955);},'A型适配板位于转子入壳端附近，用两颗长螺丝与对应M4螺母连接壳体。','x');
for(let i=0;i<2;i++){
    const y=i===0?2.72:1.68;
    add('adapterScrew'+i,'适配板长螺丝 '+(i+1),[-1.45,y,0],[-3.2,y+(i===0?.6:-.5),1.4],5+i,g=>{screw(g,'phillips',.88);g.rotation.y=-Math.PI/2;},'红黄十字改锥操作；“1/2”是演示编号，不代表任意视角中的左上/右下。','x');
    add('adapterNut'+i,'配套 M4 螺母 '+(i+1),[-.55,y,0],[-.5,y+(i===0?1.5:-.5),-1.7],5+i,g=>{nut(g);g.rotation.y=Math.PI/2;},'与本组适配板长螺丝配合；此处不演示尚未核对的夹持细节。','x');
}
add('bearing','轴承板组件',[0,2.2,.64],[.15,2.2,3.0],7,g=>{
    ring(g,.87,.19,.17,[0,0,0],materials.dark);ring(g,.32,.12,.16,[0,0,.1],materials.metal);cylinder(g,.12,.12,.85,[0,0,.44],materials.metal);gear(g,.63,.17,[0,0,-.2],materials.gear);
},'板、轴承、输出轴与背面大齿轮按现有组件粒度一起移动；外观贴合不证明啮合或扭矩合格。');
for(let i=0;i<2;i++){
    const x=i===0?-.59:.59;const y=i===0?2.65:1.75;
    add('bearingScrew'+i,'轴承板螺丝 '+(i+1),[x,y,.77],[x+(i===0?-.5:.5),y,3.6],8+i,g=>screw(g),'A型使用绿黑Torx六瓣梅花改锥，固定轴承板与壳体。');
}
add('lever','拨杆小组件',[.54,1.42,.71],[2.65,1.1,1.8],10,g=>{
    box(g,[.56,.12,.13],[0,0,0],materials.dark);ring(g,.12,.058,.05,[-.19,0,.1],materials.metal);
    const pts=[];for(let i=0;i<130;i++){const a=i/129*Math.PI*12;pts.push(new THREE.Vector3(.17+.065*Math.cos(a),-.13+i/129*.24,.14+.065*Math.sin(a)));}g.add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),100,.014,6,false),materials.metal));
},'拨杆、弹簧、垫圈按组件组展示；三者的相对摆放是展示布局，不是已确认的装配叠放。');
add('leverScrew','拨杆螺丝',[.37,1.42,.96],[2.55,1.1,2.6],11,g=>screw(g,'torx',.32),'绿黑Torx；固定拨杆小组件。紧固圈数和深度不代表实测值。');
add('handle','防振侧手柄',[1.28,2.2,.03],[3.8,2.2,-.25],12,g=>{
    cylinder(g,.075,.075,.42,[-.19,0,0],materials.metal,'x');cylinder(g,.34,.34,.12,[.07,0,0],0x222c33,'x');cylinder(g,.22,.26,1.4,[.8,0,0],0x27343e,'x');
    for(let i=0;i<8;i++)ring(g,.252,.2,.026,[.25+i*.15,0,0],0x43535a,'x');
},'通过自身螺纹柱旋入壳体侧孔；徒手转动侧手柄并不自动构成异常。','x');
const partsA=parts;parts=new Map();
buildModelB({add,ring,box,cylinder,gear,screw,nut,materials});
const partsB=parts;parts=partsA;
const tool=new THREE.Group();scene.add(tool);
let currentTool='';
function makeTool(kind){
    if(currentTool===kind)return;
    while(tool.children.length){const node=tool.children[0];tool.remove(node);node.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});}currentTool=kind;
    if(kind==='wrench'){
        box(tool,[.12,1.05,.07],[0,.68,0],0xb8c6cd);ring(tool,.19,.105,.065,[0,0,0],0xb8c6cd);ring(tool,.17,.11,.065,[0,1.26,0],0xb8c6cd);return;
    }
    if(kind==='phillips'||kind==='torx'||kind==='flat'){
        cylinder(tool,.034,.034,.85,[0,0,.43],kind==='phillips'?0xc24037:0xbfc9d1);cylinder(tool,.115,.14,.66,[0,0,1.18],kind==='phillips'?0xb94831:0x1d3037);
        const accent=kind==='phillips'?0xf6cd58:kind==='torx'?0x47b597:0x5899de;
        for(let i=0;i<5;i++){const a=i*Math.PI*2/5;const rib=box(tool,[.035,.055,.37],[Math.cos(a)*.105,Math.sin(a)*.105,1.17],accent);rib.rotation.z=a;}
        if(kind==='phillips'){box(tool,[.07,.018,.09],[0,0,.015],0xc0ccd1);box(tool,[.018,.07,.09],[0,0,.015],0xc0ccd1);}else if(kind==='flat')box(tool,[.075,.018,.09],[0,0,.015],0xc0ccd1);else{cylinder(tool,.025,.025,.075,[0,0,.015],0xc0ccd1);for(let i=0;i<6;i++){const a=i*Math.PI/3;cylinder(tool,.01,.01,.075,[Math.cos(a)*.027,Math.sin(a)*.027,.015],0xc0ccd1);}}
    }
}
const stepsA=[
    {title:'识别壳体与连接方向',ids:['housing'],tool:'none',description:'壳体是本次装配的主体。先观察转子入口、齿轮腔、轴承板接口和侧手柄连接口。',check:'不要把传动轴与轴承板上的输出轴混为一件。'},
    {title:'传动轴组件对位进入壳体',ids:['rotor'],tool:'hand',description:'轴组件沿对应入口进入壳体。风扇轮、转子和长轴在这里按一个组件表示。',check:'对位与支撑是有效操作；徒手转轴并不自动证明Handling。'},
    {title:'小锥齿轮在轴端就位',ids:['pinion'],tool:'hand',description:'小锥齿轮与传动轴端的连接关系可在透视模式下观察。',check:'实际齿形和啮合未建模。不要用动画推断实际啮合已正确。'},
    {title:'操作内部保持螺母',ids:['shaftNut'],tool:'wrench',description:'螺母先就位，再由银色两用扳手操作。保持螺母将小锥齿轮留在轴端。',check:'转动轴不等于旋紧螺母；核对实际接触与相对运动。M4/M6冲突不在这里强行裁定。'},
    {title:'适配板对位',ids:['adapter'],tool:'hand',description:'A型适配板在转子进入壳体的一侧。确认配合方向和两组紧固连接。',check:'环形件的外观与安装位置按A型参照；不要套到B型。'},
    {title:'适配板长螺丝 1 与配套螺母',ids:['adapterScrew0','adapterNut0'],tool:'phillips',description:'第一组长螺丝和M4螺母配合，将适配板连接到壳体。红黄十字改锥操作螺丝端。',check:'确认十字批头与实际螺丝槽口接触；工具颜色只是识别线索。'},
    {title:'适配板长螺丝 2 与配套螺母',ids:['adapterScrew1','adapterNut1'],tool:'phillips',description:'第二组同样使用长螺丝与M4螺母。不能只操作一颗就认定整个适配板完成。',check:'两组连接均需确认；动画编号不等于画面固定的左上／右下。'},
    {title:'轴承板组件对位',ids:['bearing'],tool:'hand',description:'轴承板及其背面大齿轮作为组件进入壳体接口。可透视观察它与内部传动件的位置关系。',check:'外观贴合不代表内部齿轮正确啮合，也不代表已紧固。'},
    {title:'轴承板螺丝 1',ids:['bearingScrew0'],tool:'torx',description:'A型手册使用绿黑Torx六瓣梅花改锥操作轴承板固定螺丝。',check:'Torx不是内六角；具体槽口和接触仍需视频证据。'},
    {title:'轴承板螺丝 2',ids:['bearingScrew1'],tool:'torx',description:'操作第二颗轴承板螺丝，核对板与壳体的两处连接。',check:'动画不提供圈数或扭矩要求，不要从旋转次数判断实际完成。'},
    {title:'识别拨杆、弹簧与垫圈',ids:['lever'],tool:'hand',description:'三种小件以组件组展示。这里只说明配套关系，不演示未经确认的精确叠放顺序。',check:'小件在模型中的间隔是展示布局；需要近景或明确手册才能核实实际叠放。',limit:'此步只表示组件组连接位置；内部装配细节未确认。'},
    {title:'拨杆螺丝',ids:['leverScrew'],tool:'torx',description:'拨杆螺丝使用绿黑Torx改锥。操作时核对小件是否被正确控制和保持。',check:'实际是否滑脱、散落或支撑失败，必须从视频观察，不能由徒手动作直接推断。'},
    {title:'侧手柄旋入侧孔',ids:['handle'],tool:'hand',description:'侧手柄使用自身的螺纹柱与壳体侧孔连接；不用前面五颗独立螺丝固定。',check:'手柄可以徒手旋转。它与独立步骤的相对先后顺序不必唯一。'},
    {title:'观察整体连接关系',ids:[],tool:'none',description:'查看轴组件、适配板、轴承板、拨杆小组件和侧手柄的连接。可以暂停、旋转或分解观察。',check:'这是结构示意终态，不表示经过机械、扭矩或功能验证。'}
];
const toolNames={none:['无工具操作','本步用于观察结构。'],hand:['徒手对位 / 支撑','模型不演示具体手指轨迹和施力。'],wrench:['银色两用扳手','保持螺母；小扳手不是螺丝刀。'],phillips:['红黄十字改锥','对应A型适配板的两颗长螺丝。'],torx:['绿黑 Torx 六瓣梅花改锥','对应A型轴承板螺丝和拨杆螺丝。'],flat:['黑蓝一字改锥','按已观察B轴承板拆卸样例示意。']};
const removeTitlesA={0:'回看壳体与已分离部件',1:'分离传动轴组件',2:'取下小锥齿轮',3:'松开内部保持螺母',4:'分离适配板',5:'解除适配板紧固连接 1',6:'解除适配板紧固连接 2',7:'取下轴承板组件',8:'松开轴承板螺丝 1',9:'松开轴承板螺丝 2',10:'收纳拨杆小组件',11:'松开拨杆螺丝',12:'旋出侧手柄',13:'观察拆卸前的连接'};
const removeDescriptionsA=[
    '部件已分开展示，可回看壳体接口。实际归置位置依现场要求，不由本动画指定。',
    '相关保持连接解除后，支撑并移出传动轴组件。轴、转子与风扇轮作为一组表示。',
    '保持螺母解除后，取下轴端小锥齿轮；不把直接转动轴当作已松开螺母。',
    '用银色两用扳手松开内部保持螺母，再取下螺母。需要观察螺母相对轴的运动。',
    '两组长螺丝与螺母已解除后，分离适配板。实际能否直接取出取决于周边组件的释放状态。',
    '用红黄十字改锥解除另一组长螺丝连接，保留并收纳对应M4螺母。',
    '用红黄十字改锥解除一组长螺丝连接，留意对应M4螺母；尚有另一组连接时不要强行分离适配板。',
    '两颗固定螺丝已解除后，分离轴承板组件。输出轴、轴承与背面大齿轮一起表示。',
    '用绿黑Torx改锥松开另一颗轴承板螺丝，支撑轴承板后再分离。',
    '用绿黑Torx改锥松开一颗轴承板螺丝；另一颗尚未解除时，轴承板仍由连接约束。',
    '拨杆螺丝解除后，控制并收纳拨杆、弹簧和垫圈；动画不指定未经确认的小件叠放次序。',
    '用绿黑Torx改锥松开拨杆螺丝，注意控制配套小件，防止意外散落。',
    '握持侧手柄，将自身螺纹柱从壳体侧孔旋出；此处徒手旋转是正常操作。',
    '拆卸前先识别各组件与连接，随后逐步解除紧固。动画展示一种顺序，独立操作可以合法换序。'
];
let mode='assemble',model=new URLSearchParams(location.search).get('model')==='B'?'B':'A',progress=0,playing=false,speed=1,explode=0,last=0,activeIndex=-1,selected=null;
let steps=stepsA,removeTitles=removeTitlesA,removeDescriptions=removeDescriptionsA,duration=70;
const smooth=t=>{const x=THREE.MathUtils.clamp(t,0,1);return x*x*(3-2*x);};
function current(){const value=Math.min(progress*steps.length,steps.length-.000001);const index=Math.floor(value);return {index,base:mode==='assemble'?index:steps.length-1-index,local:value-index};}
function home(){camera.position.set(7.5,6.2,9.8);controls.target.set(-.8,2.3,.15);controls.update();}
function list(){const order=mode==='assemble'?steps.map((s,i)=>i):steps.map((s,i)=>steps.length-1-i);$('steps').replaceChildren();for(const [n,i] of order.entries()){const b=document.createElement('button');b.innerHTML=`<span>${String(n+1).padStart(2,'0')}</span>${mode==='assemble'?steps[i].title:removeTitles[i]}`;b.onclick=()=>{playing=false;explode=0;$('explode').value=0;progress=n/steps.length+.00001;activeIndex=-1;draw();};$('steps').append(b);}}
function updatePanel(info){
    if(activeIndex===info.index)return;activeIndex=info.index;
    const step=steps[info.base];$('step-counter').textContent=`${String(info.index+1).padStart(2,'0')} / ${steps.length}`;
    $('step-title').textContent=mode==='assemble'?step.title:removeTitles[info.base];
    $('scene-title').textContent=mode==='assemble'?'看清每一次连接。':'观察连接如何解除。';
    $('step-description').textContent=mode==='assemble'?step.description:removeDescriptions[info.base];
    $('tool-name').textContent=toolNames[step.tool][0];$('tool-note').textContent=step.toolNote||toolNames[step.tool][1];$('confidence').textContent=step.confidence||'手册参考';$('step-check').textContent=step.check;
    $('step-limit').textContent=step.limit||(model==='B'?'连接参照项目图，步骤和轨迹为示意；不指定唯一操作顺序、真实扭矩或公差。':'工具对应关系有手册依据；移动路径、尺寸、圈数仅作示意。独立步骤允许合法换序。');
    [...$('steps').children].forEach((e,i)=>{e.classList.toggle('active',i===info.index);e.classList.toggle('done',i<info.index);});
}
function applyModel(){
    playing=false;selected=null;$('selected-card').hidden=true;activeIndex=-1;
    parts=model==='A'?partsA:partsB;steps=model==='A'?stepsA:stepsB;
    removeTitles=model==='A'?removeTitlesA:removeTitlesB;removeDescriptions=model==='A'?removeDescriptionsA:removeDescriptionsB;
    duration=steps.length*5;progress=0;explode=0;$('explode').value=0;$('model').value=model;
    $('model-kicker').textContent=model==='A'?'MODEL A / CG15-125BL':'MODEL B / WSG7-115A';
    for(const collection of [partsA,partsB])for(const p of collection.values()){p.g.visible=collection===parts;p.label.hidden=collection!==parts;}
    $('b-reference').hidden=model!=='B';
    list();home();draw();
}
function draw(){
    const info=current();updatePanel(info);
    const highlighted=new Set(steps[info.base].ids);
    const show=$('show-labels').checked;
    const labelBoxes=[];
    for(const [id,p] of parts){
        if(!p.g.visible){p.label.style.opacity='0';continue;}
        let installed;
        if(mode==='assemble')installed=p.step<info.base?1:p.step>info.base?0:smooth(info.local/.78);
        else installed=p.step<info.base?1:p.step>info.base?0:1-smooth(info.local/.78);
        if(id==='housing')installed=1;
        const final=p.assembled.clone();const separate=p.exploded.clone();
        p.g.position.lerpVectors(separate,final,installed);p.g.position.lerp(separate,explode);
        p.g.quaternion.copy(p.baseQ);
        const turns=highlighted.has(id)&&/Screw|shaftNut|handle/.test(id)?4*Math.PI*smooth((info.local-.36)/.52):0;
        if(turns){const axis=p.axis==='x'?new THREE.Vector3(1,0,0):new THREE.Vector3(0,0,1);const orientation=id.startsWith('adapterScrew')?1:-1;p.g.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(axis,turns*orientation*(mode==='assemble'?1:-1)));}
        for(const m of p.meshes){m.material.emissive.setHex(highlighted.has(id)?0xb56d28:selected===id?0x2d6684:0);m.material.emissiveIntensity=highlighted.has(id)?.32:.2;if(id==='housing'){m.material.transparent=$('xray').checked;m.material.opacity=$('xray').checked?.24:1;m.material.depthWrite=!$('xray').checked;}}
        p.label.classList.toggle('active',highlighted.has(id));
        const location=p.g.position.clone().add(new THREE.Vector3(0,.3,0)).project(camera);
        const display=show&&location.z<1&&(highlighted.has(id)||selected===id||(explode>.15)||(!id.includes('Screw')&&!id.includes('Nut')&&id!=='shaftNut'));
        let labelX=(location.x*.5+.5)*viewport.clientWidth,labelY=(-location.y*.5+.5)*viewport.clientHeight;
        if(display){const width=p.label.offsetWidth||100;labelX=THREE.MathUtils.clamp(labelX,width/2+5,viewport.clientWidth-width/2-5);for(let attempt=0;attempt<10;attempt++){if(!labelBoxes.some(b=>Math.abs(b.x-labelX)<(b.width+width)/2+4&&Math.abs(b.y-labelY)<26))break;labelY-=27;}labelBoxes.push({x:labelX,y:labelY,width});}
        p.label.style.opacity=display?'1':'0';p.label.style.left=labelX+'px';p.label.style.top=labelY+'px';
    }
    tool.visible=false;
    if(explode<.01){const s=steps[info.base];if(['wrench','torx','phillips','flat'].includes(s.tool)){
        const p=parts.get(s.ids[0]);makeTool(s.tool);tool.visible=info.local>.36&&info.local<.94;
        tool.position.copy(p.g.position);const approach=(1-smooth((info.local-.36)/.18))*.8;
        if(s.tool==='wrench'){tool.quaternion.setFromAxisAngle(new THREE.Vector3(0,1,0),Math.PI/2);tool.position.x+=.04+approach;tool.rotateZ(Math.sin(info.local*Math.PI*6)*.45);}
        else{tool.quaternion.copy(p.baseQ);tool.position.add(new THREE.Vector3(0,0,.08+approach).applyQuaternion(p.baseQ));tool.rotateZ((mode==='assemble'?-1:1)*info.local*Math.PI*8);}
    }}
    $('play').textContent=playing?'暂停':'播放';$('progress').value=progress;
    const seconds=Math.round(progress*duration);$('position').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')} / ${String(Math.floor(duration/60)).padStart(2,'0')}:${String(duration%60).padStart(2,'0')} · ${Math.round(progress*100)}%`;
    renderer.render(scene,camera);
}
function togglePlay(){if(progress>=1)progress=0;explode=0;$('explode').value=0;playing=!playing;draw();}
$('play').onclick=togglePlay;
$('progress').oninput=e=>{playing=false;progress=Number(e.target.value);explode=0;$('explode').value=0;draw();};
$('speed').onchange=e=>{speed=Number(e.target.value);};
for(const [id,delta] of [['previous',-1],['next',1]])$(id).onclick=()=>{playing=false;progress=THREE.MathUtils.clamp((current().index+delta)/steps.length+.00001,0,1);explode=0;$('explode').value=0;draw();};
for(const id of ['assemble','disassemble'])$(id).onclick=()=>{mode=id;progress=0;playing=false;explode=0;$('explode').value=0;activeIndex=-1;$('assemble').classList.toggle('active',id==='assemble');$('disassemble').classList.toggle('active',id==='disassemble');list();draw();};
$('explode').oninput=e=>{playing=false;explode=Number(e.target.value);draw();};
$('restore').onclick=()=>{explode=0;$('explode').value=0;draw();};
$('model').onchange=e=>{model=e.target.value;const url=new URL(location.href);url.searchParams.set('model',model);history.replaceState(null,'',url);applyModel();};
$('home').onclick=home;
$('front').onclick=()=>{camera.position.set(-.7,2.7,11);controls.target.set(-.7,2.2,0);controls.update();};
$('top').onclick=()=>{camera.position.set(-.7,13,.1);controls.target.set(-.7,2.2,0);controls.update();};
$('focus').onclick=()=>{const p=parts.get(steps[current().base].ids[0]||'housing');controls.target.copy(p.g.position);camera.position.copy(p.g.position).add(new THREE.Vector3(3,2.5,4));controls.update();};
$('xray').onchange=draw;$('show-labels').onchange=draw;
document.addEventListener('keydown',e=>{if(['INPUT','SELECT','BUTTON'].includes(e.target.tagName))return;if(e.code==='Space'){e.preventDefault();togglePlay();}});
const raycaster=new THREE.Raycaster();let down=null;
renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
renderer.domElement.addEventListener('pointerup',e=>{
    if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
    const rect=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),camera);
    const hits=raycaster.intersectObjects([...parts.values()].filter(p=>p.g.visible).map(p=>p.g),true);
    const hit=hits.find(h=>!$('xray').checked||h.object.userData.part!=='housing')||hits[0];
    if(hit){selected=hit.object.userData.part;const p=parts.get(selected);$('selected-card').replaceChildren();const title=document.createElement('strong');title.textContent=p.name;const description=document.createElement('small');description.textContent=p.note;$('selected-card').append(title,description);$('selected-card').hidden=false;}else{selected=null;$('selected-card').hidden=true;}draw();
});
function resize(){camera.aspect=viewport.clientWidth/viewport.clientHeight;camera.updateProjectionMatrix();renderer.setSize(viewport.clientWidth,viewport.clientHeight);draw();}
new ResizeObserver(resize).observe(viewport);
applyModel();$('loading').hidden=true;
function tick(time){const dt=last?Math.min((time-last)/1000,.1):0;last=time;if(playing){progress=Math.min(1,progress+dt*speed/duration);if(progress>=1)playing=false;}controls.update();draw();requestAnimationFrame(tick);}
window.assemblyViewer={getState:()=>({model,mode,progress,playing,step:current().base,stepCount:steps.length,parts:[...parts.keys()],positions:Object.fromEntries([...parts].map(([id,p])=>[id,p.g.position.toArray()])),webgl:renderer.capabilities.isWebGL2,tool:steps[current().base].tool,toolVisible:tool.visible}),seek:value=>{playing=false;progress=THREE.MathUtils.clamp(value,0,1);draw();}};
requestAnimationFrame(tick);
