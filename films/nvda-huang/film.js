// film.js —— 《一个人，两万七千亿美元》
// 一句话账：一个人辞职，四天里市场抹掉 2.7 万亿美元。
// 素材：assets/img/huang.jpg（Wikimedia Commons，CC 授权）；头条是文字卡，标注来源与日期。
window.ready=(async()=>{
const F=await FB.init({
 counts:['assets/clips/counts.json'],
 cuts:[],
 fonts:KIT.FONTS,
});
const K=await KIT.use(F);
const PH='assets/kit/ph/';

await K.film([
 {scene:'headlines', until:'@b02', says:'这不是传闻：四家媒体同时把它放上头版',
  items:[
   {src:'CNBC', date:'2026-11-12', title:'Nvidia stock closes down 4% after CEO Jensen Huang announces resignation'},
   {src:'NBC NEWS', date:'2026-11-12', title:'Nvidia stock falls after Huang resigns, weighing on broader market'},
   {src:'REUTERS', date:'2026-11-12', title:'Equities close lower as Nvidia drop outweighs energy gains'},
   {src:"BARRON'S", date:'2026-11-19', title:'Nvidia Stock Drops Below $150 Support After Jensen Huang Scandal'},
  ],
  pick:{i:0, at:'@b01:辞呈'}},

 {scene:'line', until:'@b03', says:'市场不是情绪，是一条可以从 239 读到 125 的线',
  title:'英伟达 · 收盘价', en:'NVDA · CLOSE',
  data:{points:[
   ['2026-10-06',239.24],['2026-10-13',228.52],['2026-10-20',216.47],['2026-10-27',217.94],
   ['2026-11-03',206.69],['2026-11-05',181.60],['2026-11-10',168.89],['2026-11-12',166.19],
   ['2026-11-13',162.85],['2026-11-16',156.14],['2026-11-18',150.96],['2026-11-20',125.53]]},
  draw:{at:'@b02'},
  marks:[{at:'@b02:十六', date:'2026-11-12', text:'辞去 CEO', value:166.19}],
  focus:{at:'@b03:二点七', from:'2026-10-06', value:'−47%', brow:'从 10 月 6 日高点'}},

 {scene:'number', until:'@b04', says:'把 47% 换成钱：一个月蒸发 2.7 万亿美元',
  value:'$2.7万亿', brow:'10 月高点以来 · 蒸发', en:'MARKET CAP WIPED OUT',
  sub:'从 $5.8 万亿 → $3.05 万亿'},

 {scene:'profile', until:'@b05', says:'跌的不是抽象指数，是一个干了 33 年的人',
  name:'黄仁勋', en:'JENSEN HUANG', title:'英伟达 CEO · 1993—2026', color:'green',
  photo:'assets/img/huang.jpg',
  facts:[{text:'掌舵 33 年', at:'@b04:三十三年'},{text:'AI 的水和电', at:'@b04:水和电'}]},

 {scene:'headlines', until:'@b07', says:'起因是三篇报道，不是业绩',
  items:[
   {src:'FINANCIAL TIMES', date:'2026-11-07', title:'报道称黄仁勋与一名女高管有私情，美方情报官员认为她为中国从事间谍活动'},
   {src:'STATEMENT', date:'2026-11-08', title:'黄仁勋发表声明，承认自己对妻子不忠'},
   {src:'THE NEW YORK TIMES', date:'2026-11-12', title:'再曝：他与一名直接向他汇报的副总裁也有过关系'},
   {src:'CNBC', date:'2026-11-12', title:'董事会宣布他立即辞去 CEO 与董事职务'},
  ],
  pick:{i:0, at:'@b05:金融时报'}},

 {scene:'timeline', until:'@b09', says:'五天，从一篇报道走到辞职',
  nodes:[
   {year:'11/07', title:'FT 曝出私情', at:'@b07'},
   {year:'11/08', title:'承认对妻子不忠', at:'@b07:11月8日'},
   {year:'11/12', title:'NYT 再曝内部关系', at:'@b08:四天后'},
  ]},

 {scene:'discs', until:'@b10', says:'谁接了他的位置：临时 CEO + 首任董事长',
  items:[
   {id:'h', name:'黄仁勋', color:'green', at:'@b09'},
   {id:'k', name:'克雷斯', color:'blue', at:'@b09:克雷斯', tag:'代理 CEO'},
   {id:'j', name:'琼斯', color:'amber', at:'@b09:琼斯', tag:'首任董事长'},
  ]},

 {scene:'statement', until:'@b11', says:'提出全片的问题：一个人的去留凭什么定价',
  lines:['一家公司换个 CEO','凭什么让整个市场','跟着抖？'],
  hl:['凭什么'], at:['@b10:CEO','@b10:凭什么','@b10:抖']},

 {scene:'network', until:'@b13', says:'因为它是标普 500 的大权重，是整条 AI 链的地基',
  nodes:[
   {id:'nvda', name:'英伟达', color:'green', at:'@b11'},
   {id:'tsmc', name:'台积电', at:'@b11:地基'},
   {id:'msft', name:'微软', at:'@b11:地基'},
   {id:'openai', name:'OpenAI', at:'@b11:地基'},
   {id:'cloud', name:'云厂商', at:'@b11:地基'},
  ],
  links:[{from:'tsmc',to:'nvda'},{from:'nvda',to:'msft'},{from:'nvda',to:'openai'},
   {from:'nvda',to:'cloud'},{from:'openai',to:'msft'}],
  steps:[{at:'@b12', focus:'nvda'}]},

 {scene:'change', until:'@b14', says:'从 5.8 万亿到 3.05 万亿，47% 不是形容词',
  from:{value:'$5.8万亿', label:'10 月 6 日 · 市值'},
  to:{value:'$3.05万亿', label:'11 月 20 日 · 市值', at:'@b13:三点零五'},
  mult:'−47%'},

 {scene:'flow', until:'@b16', says:'麻烦一件接一件：绯闻 → 调查 → 监管 → 诉讼',
  nodes:[
   {id:'a', text:'绯闻曝光', pos:[0,0]},
   {id:'b', text:'董事会独立调查', pos:[1,0]},
   {id:'c', text:'SEC 查会计处理', pos:[2,0]},
   {id:'d', text:'股东集体诉讼', pos:[3,0]},
  ],
  links:[{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'d'}],
  steps:[{at:'@b14', focus:'a'},{at:'@b15', focus:'c'}]},

 {scene:'stats', until:'@b17', says:'同一天三个数字：又跌 14%、目标价腰斩、市值 3.05 万亿',
  items:[
   {label:'当日跌幅', value:'−14%', at:'@b16:百分之十四'},
   {label:'Bernstein 目标价', value:'400→200', at:'@b16:四百美元'},
   {label:'市值', value:'$3.05万亿', at:'@b16:两百'},
  ]},

 {scene:'statement', until:'@b18', says:'从绯闻升级成国家安全问题',
  lines:['董事会另外查一件事：','他是不是','被外国情报机构盯上了'],
  hl:['外国情报机构'], at:['@b17','@b17:外国','@b17:盯上']},

 {scene:'timeline', until:'@b20', says:'董事会关门，总统开口',
  nodes:[
   {year:'11/16', title:'传董事会正商讨让他回归', at:'@b18'},
   {year:'11/21', title:'董事会拒绝回归请求', at:'@b18:董事会'},
   {year:'11/22', title:'特朗普公开喊话：重新聘用他', at:'@b19'},
  ]},

 {scene:'statement', until:'@b21', says:'CEO 人选变成总统议题，这是最反常的一层',
  lines:['一家公司的 CEO 人选','变成了','总统的议题'],
  hl:['总统的议题'], at:['@b20:CEO','@b20:总统','@b20:议题']},

 {scene:'stats', until:'@b23', says:'33 年 vs 4 天，量级对比',
  items:[
   {label:'掌舵英伟达', value:'33 年', at:'@b21:三十三年'},
   {label:'市值做到', value:'$5.8万亿', at:'@b21:五点八'},
   {label:'交出去用了', value:'4 天', at:'@b22'},
  ]},

 {scene:'statement', says:'落到判断：市场怕的是没有第二个人',
  lines:['市场怕的不是绯闻','也不是证交会','是找不到第二个人'],
  hl:['第二个人'], at:['@b23:绯闻','@b23:证交会','@b24:第二个']},
]);
return K.go();
})();
