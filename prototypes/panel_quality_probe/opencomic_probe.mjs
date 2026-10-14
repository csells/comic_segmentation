// Run the pinned, unchanged OpenComic panel API; component indices are NOT reading order.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const [packageRoot, imageRoot, output, model] = process.argv.slice(2);
fs.mkdirSync(output); // Exclusive run directory.
const {default: OpenComicAI} = await import(path.resolve(packageRoot,'dist/index.mjs'));
const require = createRequire(path.resolve(packageRoot,'package.json'));
const {default: sharp} = await import(require.resolve('sharp'));
OpenComicAI.setSharp(sharp);
OpenComicAI.setModelsPath(path.resolve(packageRoot,'models'));
OpenComicAI.concurrentDaemons=0;
OpenComicAI.panels.debug=true;
const results=[];
for(const [i,page] of [5,25,254,256].entries()){
 const folder=path.join(output,`page-${String(page).padStart(4,'0')}`);fs.mkdirSync(folder);
 OpenComicAI.panels.tempDir=path.resolve(folder);
 const source=path.resolve(imageRoot,`${String(page).padStart(4,'0')}.jpg`);
 const options={model,gpuId:'0',threads:1};
 fs.writeFileSync(path.join(folder,'request.json'),JSON.stringify({source,source_sha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),options,ordering:'upstream connected components, not narrative order'},null,2));
 console.log(`[${i+1}/4] PDF ${page}: OpenComic ${model} started`);
 const start=Date.now();
 try{
 const detection=await OpenComicAI.panels.image(source,options);
 fs.writeFileSync(path.join(folder,'detections.json'),JSON.stringify({...detection,boxes:detection.boxes.map(({mask,...b})=>b)},null,2));
 results.push({source_page:page,status:'unreviewed_components',count:detection.boxes.length,elapsed_seconds:(Date.now()-start)/1000});
 console.log(`[${i+1}/4] PDF ${page}: ${detection.boxes.length} components in ${(Date.now()-start)/1000}s`);
 }catch(e){results.push({source_page:page,status:'failed',error:String(e)});fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));throw e;}
 fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));
}
