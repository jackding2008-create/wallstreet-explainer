// film.js —— 《买一座矿，要走十五年》
// 一句话账：买矿不是买资源，是买下一条十五年的流水线，每一步都会重新定价。
// 素材：assets/img/*.jpg 全部来自 Wikimedia Commons（CC 授权，见 assets.txt）；
// 数据：S&P Global 2024、JORC 2012、发改委 11 号令、商务部境外投资管理办法、中信泰富 Sino Iron 案、紫金卡莫阿。
window.ready=(async()=>{
const F=await FB.init({
 counts:['assets/clips/counts.json'],
 cuts:[],
 fonts:KIT.FONTS,
});
const K=await KIT.use(F);

await K.film([
 {scene:'statement', until:'@b02', says:'开场把代价摆上桌：买 4 亿，建成 98 亿，赔 300 亿',
  brow:'西澳 · 磁铁矿',
  lines:['4.15 亿美元买下','98 亿美元建成','300 亿人民币赔掉'],
  hl:['赔掉'], at:['@b01:4.15','@b02:98亿','@b02:300亿'],
  items:['assets/img/pit.jpg']},

 {scene:'flow', until:'@b03', says:'先把整条流水线摊开：六段，十几年',
  nodes:[
   {id:'a', title:'找矿与谈判', pos:[0,0]},
   {id:'b', title:'尽职调查', pos:[1,0]},
   {id:'c', title:'中国审批', pos:[2,0]},
   {id:'d', title:'勘探与可研', pos:[0,1]},
   {id:'e', title:'融资与矿建', pos:[1,1]},
   {id:'f', title:'开采与闭矿', pos:[2,1]},
  ],
  links:[{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'d'},{from:'d',to:'e'},{from:'e',to:'f'}],
  steps:[{at:'@b03:流水线', focus:'a'}]},

 {scene:'number', until:'@b05', says:'15.7 年，其中 11.9 年还没动土',
  value:'15.7年', brow:'从发现到出矿 · 127 座矿', en:'S&P GLOBAL',
  at:'@b04:15.7',
  sub:{label:'其中 · 勘探与研究', value:'11.9年', at:'@b05:11.9'}},

 {scene:'footage', until:'@b07', says:'找矿从岩芯开始：先看石头，再看钱',
  img:'assets/img/core.jpg', push:[1,1.07], focus:[900,520],
  badge:{name:'第一步 · 找矿', color:'amber', at:'@b06'}},

 {scene:'compare', until:'@b09', says:'资源量不是储量，中间隔着一整套修正因素',
  left:{title:'资源量', color:'blue'}, right:{title:'矿石储量', color:'gold'},
  rows:[
   {label:'是什么', left:'地里的矿', right:'能赚钱的矿', at:'@b07:赚钱'},
   {label:'分几级', left:'推断/控制/探明', right:'概略/证实', at:'@b08:推断'},
   {label:'怎么转', left:'控制以上', right:'要过修正', at:'@b09:修正'}],
  brow:'JORC 2012'},

 {scene:'flow', until:'@b12', says:'价格只是开场，真正定价的是这四件事',
  nodes:[
   {id:'a', title:'权益金', pos:[0,0]},
   {id:'b', title:'或有对价', pos:[1,0]},
   {id:'c', title:'审批条件', pos:[2,0]},
   {id:'d', title:'基础设施', pos:[3,0]},
  ],
  links:[{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'d'}],
  steps:[{at:'@b11:权益金', focus:'a'},{at:'@b11:对价', focus:'b'},
   {at:'@b11:审批', focus:'c'},{at:'@b11:基础设施', focus:'d'}]},

 {scene:'quote', until:'@b13', says:'两个字，判出每年 2 亿澳元、赔 30 年',
  text:'“取走”两个字，判成每年 2 亿澳元，赔 30 年',
  who:{name:'西澳最高法院', title:'2017 年终审 · Sino Iron', color:'red'},
  hl:['30 年'], hlAt:'@b12:30年', source:'Reuters'},

 {scene:'flow', until:'@b15', says:'五条线同时查，任何一条塌了都要重定价',
  nodes:[
   {id:'a', title:'地质', pos:[0,0]},
   {id:'b', title:'冶金', pos:[1,0]},
   {id:'c', title:'法律', pos:[2,0]},
   {id:'d', title:'税务', pos:[0,1]},
   {id:'e', title:'社区', pos:[1,1]},
  ],
  links:[{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'d'},{from:'d',to:'e'}],
  steps:[{at:'@b14:地质', focus:'a'},{at:'@b14:冶金', focus:'b'},{at:'@b14:法律', focus:'c'},
   {at:'@b14:税务', focus:'d'},{at:'@b14:社区', focus:'e'}]},

 {scene:'footage', until:'@b17', says:'尽调花几百万，换掉的是几十亿的盲区',
  img:'assets/img/port.jpg', push:[1,1.06], focus:[1000,560],
  badge:{name:'第三步 · 尽调', color:'blue', at:'@b16:几百万'}},

 {scene:'stats', until:'@b19', says:'中国这一侧，法定时限其实很短',
  brow:'境外投资 · 中国侧',
  items:[
   {label:'发改委 · 备案', value:'7 个工作日', at:'@b18:7个工作日'},
   {label:'商务部 · 备案', value:'3 个工作日', at:'@b18:3个工作日'},
   {label:'实务全程', value:'1–2 个月', at:'@b19:一到两个月'}]},

 {scene:'timeline', until:'@b22', says:'从预可研到可研，一两年只是起步',
  nodes:[
   {year:'6–12 个月', title:'预可研 PFS', at:'@b21:6到12'},
   {year:'12–24 个月', title:'可行性研究 DFS', at:'@b21:12到24'},
  ]},

 {scene:'flow', until:'@b25', says:'几十亿的资本开支，靠四条管道凑出来',
  nodes:[
   {id:'a', title:'股东贷款', pos:[0,0]},
   {id:'b', title:'银团', pos:[1,0]},
   {id:'c', title:'政策性银行', pos:[2,0]},
   {id:'d', title:'包销协议', pos:[3,0]},
  ],
  links:[{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'d'}],
  steps:[{at:'@b24:股东贷款', focus:'a'},{at:'@b24:银团', focus:'b'},
   {at:'@b24:政策性银行', focus:'c'},{at:'@b24:包销', focus:'d'}]},

 {scene:'number', until:'@b26', says:'紫金买卡莫阿只花 4.12 亿美元，买的是 49.5%',
  value:'$4.12亿', brow:'卡莫阿 · 2015 年', en:'KAMOA · IVANHOE',
  at:'@b25:4.12',
  sub:{label:'收购权益', value:'49.5%', at:'@b25:49.5'}},

 {scene:'footage', until:'@b27', says:'矿建是把图纸变成能运转的厂',
  img:'assets/img/truck.jpg', push:[1,1.08], focus:[820,540],
  badge:{name:'第七步 · 矿建', color:'amber', at:'@b26'}},

 {scene:'change', until:'@b28', says:'EPC 合同 11 亿，最后结算 98 亿',
  from:{value:'$11亿', label:'EPC 合同价'},
  to:{value:'$98亿', label:'最终造价', at:'@b27:98亿'},
  mult:'×8.9'},

 {scene:'footage', until:'@b29', says:'开采之后，每天都要算成本',
  img:'assets/img/plant.jpg', push:[1,1.06], focus:[980,540],
  badge:{name:'第八步 · 开采', color:'green', at:'@b28'}},

 {scene:'stats', until:'@b30', says:'两把尺子：C1 和 AISC',
  brow:'铜 · 成本口径',
  items:[
   {label:'C1 · 现金成本', value:'采矿+选矿', at:'@b29:C1'},
   {label:'AISC · 全维持', value:'$1.7–3.8/lb', at:'@b29:AISC'},
   {label:'行业常见', value:'$2.5/lb', at:'@b29:2.5'}]},

 {scene:'change', until:'@b31', says:'同一座矿，资源量从 2400 涨到 4249 万吨',
  from:{value:'2400万吨', label:'2015 年 · 铜资源量'},
  to:{value:'4249万吨', label:'后来 · 铜资源量', at:'@b31:4249'},
  mult:'×1.8'},

 {scene:'statement', until:'@b33', says:'闭矿不是结束，是三十年的账单',
  lines:['最后一步：闭矿','保证金第一天就要备','责任跟着矿一辈子'],
  hl:['一辈子'], at:['@b32:闭矿','@b33:第一天','@b33:一辈子'],
  items:['assets/img/pit.jpg']},

 {scene:'montage', until:'@b34', says:'这条流水线，才是被买回来的东西',
  items:['assets/img/core.jpg','assets/img/pit.jpg','assets/img/truck.jpg',
   'assets/img/plant.jpg','assets/img/port.jpg'],
  pin:{value:'15年', brow:'发现 → 出矿'}},

 {scene:'statement', says:'收在判断：便宜不重要，算得清才重要',
  lines:['不是买得便宜','是买完之后','每一步都算得清'],
  hl:['算得清'], at:['@b35:便宜','@b35:买完之后','@b35:算得清']},
]);
return K.go();
})();
