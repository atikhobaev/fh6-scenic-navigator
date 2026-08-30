import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const root=process.cwd();
const input=path.join(root,'static','styles','app.css');
const output=path.join(root,'static','styles','tailwind.css');
const localCli=path.join(root,'node_modules','.bin',process.platform==='win32'?'tailwindcss.cmd':'tailwindcss');

function matchingBrace(text,open){
  let depth=0;
  for(let i=open;i<text.length;i++){
    if(text[i]==='{')depth++;
    else if(text[i]==='}'&&--depth===0)return i;
  }
  throw new Error(`Unclosed CSS block at ${open}`);
}

function replaceRule(text,prefix,render){
  const start=text.indexOf(prefix);
  if(start<0)return text;
  const open=text.indexOf('{',start);
  if(open<0)throw new Error(`Missing block for ${prefix}`);
  const close=matchingBrace(text,open);
  const inner=text.slice(open+1,close);
  return text.slice(0,start)+render(inner)+text.slice(close+1);
}

function offlineCompile(source){
  let css=source.replace(/^\s*@import\s+["']tailwindcss["'];?\s*/m,'');
  css=replaceRule(css,'@theme',inner=>`:root {${inner}}`);
  css=replaceRule(css,'@layer base',inner=>inner);
  css=replaceRule(css,'@layer components',inner=>inner);
  return css.trim()+"\n";
}

if(fs.existsSync(localCli)){
  const result=spawnSync(localCli,['-i',input,'-o',output,'--minify'],{stdio:'inherit'});
  if(result.status!==0)process.exit(result.status??1);
  console.log(`[tailwind] compiled with local Tailwind CLI -> ${path.relative(root,output)}`);
}else{
  const source=fs.readFileSync(input,'utf8');
  fs.writeFileSync(output,offlineCompile(source),'utf8');
  console.log(`[tailwind] local CLI unavailable; wrote offline static build -> ${path.relative(root,output)}`);
}
