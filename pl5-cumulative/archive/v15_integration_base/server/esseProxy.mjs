/** Same-origin proxy to loopback-only Python ESSE; no external host forwarding. */
const port = Number(process.env.PL5_BRIDGE_PORT || 8765);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("Invalid PL5_BRIDGE_PORT");
const root = `http://127.0.0.1:${port}`;
const LIMIT = 700000;

function respond(res, status, obj) {
  res.writeHead(status,{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"});
  res.end(JSON.stringify(obj));
}
export async function handleEsseProxy(req,res) {
  const health=req.url==="/api/esse/health";
  if (!(health && req.method==="GET") && !(!health && req.url==="/api/esse/sculpt" && req.method==="POST")) {
    respond(res,405,{error:"method_not_allowed"});return;
  }
  if (!health && (!req.headers["content-type"]?.includes("application/json") || Number(req.headers["content-length"] || 0)>LIMIT)) {
    respond(res,413,{error:"invalid_request"});return;
  }
  try {
    let body;
    if (!health) {
      let size=0; const chunks=[];
      for await (const chunk of req) {
        size+=chunk.length;
        if (size>LIMIT) {respond(res,413,{error:"payload_too_large"});return;}
        chunks.push(chunk);
      }
      body=Buffer.concat(chunks);
    }
    const response=await fetch(root+req.url,{
      method:health?"GET":"POST",
      headers:health?undefined:{"Content-Type":"application/json"},
      body, signal:AbortSignal.timeout(45000),
    });
    const text=await response.text();
    if(text.length>1000000){respond(res,502,{error:"upstream_response_too_large"});return;}
    res.writeHead(response.status,{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"});
    res.end(text);
  } catch {
    respond(res,503,{error:"esse_backend_offline",message:"Python ESSE桥接服务未启动，先运行integration_server.py"});
  }
}
