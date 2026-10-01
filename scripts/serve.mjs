import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
const root=resolve(import.meta.dirname,'../dist');
const port=Number(process.env.PORT||4174);
const base=JSON.parse(await readFile(resolve(root,'build-info.json'),'utf8')).base;
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
http.createServer(async(req,res)=>{
  try {
    let pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(!pathname.startsWith(base)){res.writeHead(404).end('Not found');return;}
    let path=resolve(root,pathname.slice(base.length)||'.');
    if(path!==root&&!path.startsWith(root+'/')){res.writeHead(403).end('Forbidden');return;}
    if((await stat(path)).isDirectory()) path=resolve(path,'index.html');
    const body=await readFile(path);res.writeHead(200,{'Content-Type':types[extname(path)]||'application/octet-stream','Cache-Control':'no-store'});res.end(body);
  }catch{res.writeHead(404,{'Content-Type':'text/html; charset=utf-8'}).end(await readFile(resolve(root,'404.html'),'utf8'));}
}).listen(port,'127.0.0.1',()=>console.log(`Dot小绿皮书：http://127.0.0.1:${port}${base}`));
