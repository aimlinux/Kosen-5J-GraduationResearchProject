const $=id=>document.getElementById(id);
let history=[];
function fmt(v,d=1){return v===null||v===undefined?"--":Number(v).toFixed(d)}
function draw(){
 const canvas=$("chart"), wrap=canvas.parentElement, rect=wrap.getBoundingClientRect(), dpr=window.devicePixelRatio||1;
 canvas.width=Math.max(1,Math.floor(rect.width*dpr));canvas.height=Math.max(1,Math.floor(rect.height*dpr));
 const ctx=canvas.getContext("2d");ctx.scale(dpr,dpr);const w=rect.width,h=rect.height;
 ctx.clearRect(0,0,w,h);
 if(!history.length){$("empty").style.display="grid";return}
 $("empty").style.display="none";
 const pad={l:42,r:12,t:15,b:30}, cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
 const vals=history.flatMap(r=>[Number(r.inside_temp),Number(r.room_temp)]).filter(Number.isFinite);
 let min=Math.floor(Math.min(...vals)-2),max=Math.ceil(Math.max(...vals)+2);if(max-min<6){min-=2;max+=2}
 const X=i=>pad.l+(history.length<2?cw/2:i/(history.length-1)*cw),Y=v=>pad.t+(max-v)/(max-min)*ch;
 ctx.font="11px Yu Gothic, sans-serif";ctx.lineWidth=1;
 for(let k=0;k<=4;k++){let v=min+(max-min)*k/4,y=Y(v);ctx.strokeStyle="#e8eef3";ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();ctx.fillStyle="#8493a3";ctx.textAlign="right";ctx.fillText(v.toFixed(0),pad.l-8,y+4)}
 const series=[["inside_temp","#2877b9"],["room_temp","#e79b45"]];
 for(const [key,color] of series){ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();history.forEach((r,i)=>{let x=X(i),y=Y(Number(r[key]));if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke();
  history.forEach((r,i)=>{if(i===history.length-1){ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(i),Y(Number(r[key])),4,0,Math.PI*2);ctx.fill()}})}
 ctx.fillStyle="#8493a3";ctx.textAlign="left";ctx.fillText("古い",pad.l,h-7);ctx.textAlign="right";ctx.fillText("最新",w-pad.r,h-7);
}
function showAlert(a,latest){
 const el=$("alert");el.className="alert "+(a.level||"neutral");
 const titles={unknown:"データ待機中",normal:"正常範囲（試作判定）",warning:"注意",danger:"警告"};
 $("alertTitle").textContent=titles[a.level]||"状態不明";$("alertMessage").textContent=a.message||"";
 $("alertTime").textContent=a.notify_after_min===null?"":a.notify_after_min===0?"即時確認":`通知目安 ${a.notify_after_min}分`;
}
async function load(){
 try{
  const [sr,hr]=await Promise.all([fetch("/api/status"),fetch("/api/history?limit=120")]);
  if(!sr.ok||!hr.ok)throw Error("API error");
  const s=await sr.json();history=await hr.json();const r=s.latest;
  $("connection").textContent="サーバー接続中";
  if(r){
   $("inside").textContent=fmt(r.inside_temp,1);$("room").textContent=fmt(r.room_temp,1);
   $("humidity").textContent=fmt(r.humidity,0);$("power").textContent=fmt(r.power_w,1);
   $("device").textContent=r.device_id;$("updated").textContent=new Date(r.recorded_at).toLocaleString("ja-JP");
   $("current").textContent=r.current_a==null?"—":fmt(r.current_a,2)+" A";
   $("door").textContent=r.door_open==null?"未計測":r.door_open?"開":"閉";
  }else{$("connection").textContent="データ待機中"}
  $("rise").textContent=s.alert.rise_rate==null?"—":fmt(s.alert.rise_rate,3)+" °C/分";
  showAlert(s.alert,r);draw();
 }catch(e){$("connection").textContent="接続できません"}
}
$("demoBtn").onclick=async()=>{await fetch("/api/demo",{method:"POST"});await load()};
$("refreshBtn").onclick=load;
$("clearBtn").onclick=async()=>{if(confirm("保存した計測履歴をすべて削除しますか？")){await fetch("/api/history",{method:"DELETE"});await load()}};
window.addEventListener("resize",draw);load();setInterval(load,3000);
