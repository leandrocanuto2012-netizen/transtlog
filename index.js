import express from 'express';
import { createClient } from '@supabase/supabase-js';
import cron from 'node-cron';
const app = express();
app.use(express.json());
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

async function zap(msg){
  await fetch(`https://api.z-api.io/instances/${process.env.ZAPI_ID}/token/${process.env.ZAPI_TOKEN}/send-text`,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({phone: process.env.SEU_NUMERO, message: msg})
  });
}

app.post('/webhook/estoque', async (req,res)=>{
  const p = req.body.record;
  if(p.estoque_atual < p.estoque_minimo){
    await zap(`🤖 IA Admin: ${p.nome} acabando! Só ${p.estoque_atual} - Pausado no iFood`);
  }
  res.json({ok:true});
});

async function relatorio(){
  const {data: atrasos} = await supabase.from('entregas').select('*').lt('prazo_entrega', new Date().toISOString()).neq('status','entregue');
  const {data: vendas} = await supabase.from('entregas').select('valor').gte('created_at', new Date(Date.now()-3600000).toISOString());
  const total = vendas?.reduce((s,v)=>s+(v.valor||0),0) || 0;
  let msg = `🤖 RELATÓRIO ${new Date().toLocaleTimeString('pt-BR')}\n\n`;
  msg += `🚨 Atrasados: ${atrasos?.length||0}\n💰 Última hora: R$ ${total}\n📦 Pedidos: ${vendas?.length||0}`;
  await zap(msg);
}

cron.schedule('0 * * * *', relatorio);
app.get('/', (req,res)=>res.send('IA Admin rodando!'));
app.listen(process.env.PORT||3000);