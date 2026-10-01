import {readFile,readdir,stat} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..');
const get=async name=>JSON.parse(await readFile(resolve(root,'content',name+'.json'),'utf8'));
const [chapters,faq,cases]=await Promise.all(['chapters','faq','cases'].map(get));
const unique=(items,key,label)=>assert.equal(new Set(items.map(x=>x[key])).size,items.length,`${label} ${key} 重复`);
for(const [label,items] of Object.entries({chapters,faq,cases})) {unique(items,'id',label);for(const item of items)assert.match(item.id,/^[a-z0-9-]+$/);}
assert.equal(chapters.length,8,'应提供完整8章学习路线');
assert.ok(faq.length>=50,'至少50个实用问答');
assert.ok(cases.length>0,'需要真实Dot用户案例');
const chapterIds=new Set(chapters.map(x=>x.id));
const official=link=>assert.ok(/^https:\/\/learn\.chatgpt\.com\/docs\//.test(link),`非官方产品来源：${link}`);
for(const c of chapters){assert.ok(c.sections.length>=3&&c.steps.length>=3&&c.checks.length>=3);assert.ok(c.prompt.length>50);c.sourceUrls.forEach(official);}
for(const q of faq){assert.ok(chapterIds.has(q.chapterId),`${q.id} 对应章节不存在`);assert.ok(q.question&&q.answer&&q.action&&q.sourceUrls.length);q.sourceUrls.forEach(official);}
unique(cases,'sourceUrl','cases');
for(const c of cases){
  assert.equal(c.product,'ChatGPT Dot');assert.equal(c.sourceBasis,'public-user-post');
  assert.equal(c.verification,'source-reviewed',`${c.id} 原帖尚未本轮核对`);
  assert.ok(!/gpt[\s-]*6[.．]1|6[.．]1\s*sol/i.test(JSON.stringify(c)),`${c.id} 混入被排除模型案例`);
  assert.deepEqual(Object.keys(c.scores).sort(),['evidence','goal','result','transfer','workflow']);
  const values=Object.values(c.scores);assert.ok(values.every(x=>Number.isInteger(x)&&x>=0&&x<=2));
  assert.equal(values.reduce((a,b)=>a+b,0),c.score);assert.ok(c.score>=8&&c.score<=10);
  assert.ok(c.evidence&&c.limits&&c.prompt&&c.dotRole&&c.outcome&&c.steps.length>=3);assert.match(c.sourceUrl,/^https:\/\//);
}
const output=resolve(root,'dist');
const info=JSON.parse(await readFile(resolve(output,'build-info.json'),'utf8'));
let htmlCount=0,linkCount=0;
async function walk(dir){let out=[];for(const name of await readdir(dir)){const path=resolve(dir,name);if((await stat(path)).isDirectory())out.push(...await walk(path));else out.push(path);}return out;}
const files=await walk(output),htmlFiles=files.filter(x=>x.endsWith('.html'));
const documents=new Map();
for(const path of htmlFiles){const html=await readFile(path,'utf8');const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length,`${path} HTML id 重复`);documents.set(path,{html,ids:new Set(ids)});}
const titles=[];
for(const [path,{html}] of documents){
  htmlCount++;assert.match(html,/<html lang="zh-CN">/);assert.equal((html.match(/<h1>/g)||[]).length,1);assert.match(html,/<meta name="description" content="[^"]+">/);titles.push(html.match(/<title>([^<]+)<\/title>/)[1]);
  assert.ok(!html.includes('/Users/'),'公开网页包含本机路径');assert.ok(!/<script[^>]+src="https?:/.test(html),'不应引入第三方脚本');
  for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)){
    const link=match[1].replaceAll('&amp;','&');if(/^(https?:|data:|mailto:)/.test(link))continue;linkCount++;
    const [pathname,fragment]=link.split('#');let target;
    if(!pathname)target=path;
    else if(pathname.startsWith('/')){assert.ok(pathname.startsWith(info.base),`部署路径不正确：${link}`);target=resolve(output,pathname.slice(info.base.length)||'.');}
    else target=resolve(dirname(path),pathname);
    assert.ok(target===output||target.startsWith(output+'/'));const s=await stat(target).catch(()=>null);assert.ok(s,`${path} 链接不存在：${link}`);if(s.isDirectory())target=resolve(target,'index.html');
    if(fragment&&documents.has(target))assert.ok(documents.get(target).ids.has(fragment),`${path} 锚点不存在：${link}`);
  }
}
assert.equal(new Set(titles).size,titles.length,'页面标题必须唯一');
console.log(`检查通过：${chapters.length}章、${faq.length}问答、${cases.length}个纯Dot高分案例；${htmlCount}页、${linkCount}条内部链接与锚点。`);
