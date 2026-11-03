// Run against the local build with synthetic API responses only.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const root = path.resolve(__dirname, '../dist');
const artifacts = path.resolve(process.env.TALVOA_TEST_ARTIFACTS || path.join(__dirname, '../../.test-results/pr98'));
fs.mkdirSync(artifacts, {recursive:true});
const mime = {'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml'};
const server = http.createServer((req,res) => {
  let file = path.join(root, decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root,'index.html');
  res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
  res.end(fs.readFileSync(file));
});
const companies = [1,2].map(id => ({id,name:`Cliente ${id}`,partner_id:1,customer_portal_enabled:false,active:true}));
const printer = (count,index=1) => ({id:index,name:`Printer ${index}`,ip:`192.0.2.${index}`,status:'online',model:'Synthetic',sector_name:null,page_count:count});
const results = [];
let browser;
async function main() {
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const port = server.address().port;
  browser = await chromium.launch({headless:true, ...(process.env.EDGE_EXECUTABLE_PATH ? {executablePath:process.env.EDGE_EXECUTABLE_PATH} : {})});
  async function scenario(name, body) {
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    const state = {fleetStatus:200,alertsStatus:200,summaryStatus:200,overviewStatus:200,printers:[printer(null,1),printer(0,2),printer(12345,3)],delayA:false,releaseA:null,delayedAStatus:500,printersA:null};
    page.setDefaultTimeout(10000);
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!url.pathname.startsWith('/api/v1/')) {
        if(url.hostname === '127.0.0.1') return route.continue();
        return route.abort();
      }
      const p = url.pathname.slice('/api/v1'.length);
      let data={},status=200;
      if (p === '/auth/me') data={id:1,name:'Synthetic User',email:'synthetic@example.invalid',role:'partner_admin',company_id:1,company_name:'Synthetic',active:true};
      else if (p === '/partners/me') data={platform_admin:false,partners:[{id:1,name:'Synthetic Partner',role:'partner_admin'}]};
      else if (p === '/partners/my-companies') data=companies;
      else if (p === '/partners/portfolio-summary') {status=state.summaryStatus;data={companies:2,active_printers:3,online_printers:3,offline_printers:0};}
      else if (/\/overview$/.test(p)) {status=state.overviewStatus;data={company_id:Number(p.split('/')[3]),total_active_printers:3,online_printers:3,offline_printers:0,agent_status:'healthy'};}
      else if (/\/printers$/.test(p)) {
        if(state.delayA && p.includes('/1/')) {const delayedStatus=state.delayedAStatus;const delayedData=state.printersA;await new Promise(resolve=>{state.releaseA=resolve;});status=delayedStatus;data=status===200?delayedData:{detail:'synthetic delayed failure'};}
        else {status=state.fleetStatus;data=state.printers;}
      }
      else if (/\/alerts$/.test(p)) {status=state.alertsStatus;data=[];}
      else {status=404;data={detail:'unmocked path'};}
      await route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    });
    try {
      await page.goto(`http://127.0.0.1:${port}`);
      await page.getByRole('button',{name:'Cliente 1',exact:true}).waitFor();
      await body(page,state);
      assert.deepEqual(errors,[]);
      results.push({name,status:'PASS'});
    } catch(e) {
      results.push({name,status:'FAIL',error:e.message});
      await page.screenshot({path:path.join(artifacts,`${results.length}-failure.png`),fullPage:true});
    } finally {await page.close();}
  }
  await scenario('Counters null, zero and positive', async(page,s)=>{
    await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
    await page.getByRole('columnheader',{name:'Contador total',exact:true}).waitFor();
    const rows=page.locator('tr').filter({has:page.getByRole('cell',{name:/^Printer /})});
    assert.deepEqual(await rows.evaluateAll(rows=>rows.map(row=>row.cells[4].textContent)),['—','0','12.345']);
  });
  await scenario('Printers HTTP 500 shows error, not empty inventory',async(page,s)=>{
    s.fleetStatus=500;
    await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'Nenhum dado foi atualizado'}).waitFor();
    assert.equal(await page.getByText('Nenhuma impressora cadastrada.',{exact:true}).count(),0);
    assert.equal(await page.getByRole('columnheader',{name:'Contador total'}).count(),0);
    assert.equal(await page.getByRole('button',{name:'Entrar',exact:true}).count(),0);
  });
  await scenario('Alerts HTTP 500 shows inventory query error',async(page,s)=>{
    s.alertsStatus=500;
    await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'Nenhum dado foi atualizado'}).waitFor();
    assert.equal(await page.getByText('Nenhuma impressora cadastrada.',{exact:true}).count(),0);
  });
  await scenario('Actual empty inventory',async(page,s)=>{
    s.printers=[];
    await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
    await page.getByText('Nenhuma impressora cadastrada.',{exact:true}).waitFor();
    assert.equal(await page.getByRole('alert').count(),0);
  });
  await scenario('Failed portfolio refresh hides previous indicators',async(page,s)=>{
    s.summaryStatus=500;
    await page.getByRole('button',{name:'Atualizar',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'indicadores anteriores foram ocultados'}).waitFor();
    assert.equal(await page.locator('.partner-portfolio .grid').count(),0);
    assert.equal(await page.getByRole('button',{name:'Cliente 1',exact:true}).count(),0);
  });
  await scenario('401 expires session, clears preview and returns to login',async(page,s)=>{
    await page.evaluate(()=>{sessionStorage.setItem('printflow_preview_token','synthetic-preview');sessionStorage.setItem('printflow_preview_company','synthetic-company');});
    s.fleetStatus=401;
    await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
    await page.getByRole('button',{name:'Entrar',exact:true}).waitFor();
    await page.getByText('Sua sessão expirou. Faça login novamente.',{exact:true}).waitFor();
    assert.deepEqual(await page.evaluate(()=>[sessionStorage.getItem('printflow_preview_token'),sessionStorage.getItem('printflow_preview_company')]),[null,null]);
    assert.equal(await page.locator('.partner-portfolio').count(),0);
  });
  await scenario('Partial overview HTTP 500 should not imply zero offline clients',async(page,s)=>{
    s.overviewStatus=500;
    await page.getByRole('button',{name:'Atualizar',exact:true}).click();
    await page.getByRole('button',{name:'Cliente 1',exact:true}).waitFor();
    const card=page.locator('article').filter({hasText:'Clientes com impressoras offline'});
    assert.equal(await card.locator('h2').textContent(),'—');
    await page.getByRole('alert').filter({hasText:'indicadores por empresa'}).waitFor();
  });
  await scenario('Old company error and success cannot overwrite current company inventory',async(page,s)=>{
    s.delayA=true;
    s.printers=[{...printer(12345),name:'Printer B'}];
    s.printersA=[{...printer(99999),name:'Printer A'}];
    for(const status of [500,200]) {
      s.delayedAStatus=status;
      s.releaseA=null;
      await page.getByRole('button',{name:'Cliente 1',exact:true}).click();
      await page.getByRole('button',{name:'Cliente 2',exact:true}).click();
      await page.getByRole('cell',{name:'Printer B',exact:true}).waitFor();
      assert.ok(s.releaseA);
      const responsePromise=page.waitForResponse(response=>response.url().endsWith('/companies/1/printers') && response.status()===status);
      s.releaseA();
      await (await responsePromise).finished();
      // Let React process the delayed completion before asserting the retained DOM.
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      assert.equal(await page.getByRole('cell',{name:'Printer B',exact:true}).count(),1);
      assert.equal(await page.getByRole('cell',{name:'12.345',exact:true}).count(),1);
      assert.equal(await page.getByRole('cell',{name:'Printer A',exact:true}).count(),0);
      assert.equal(await page.getByRole('alert').count(),0);
      await page.getByRole('heading',{name:'Cliente 2',exact:true}).waitFor();
    }
  });
  fs.writeFileSync(path.join(artifacts,'browser-results.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
  process.exitCode=results.some(r=>r.status==='FAIL')?1:0;
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.close();});
