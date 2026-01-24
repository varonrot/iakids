<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Panel de Padres | KidsAI</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <!-- Supabase -->
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>

  <style>
    :root{
      --bg1:#fff3e6;
      --bg2:#eaf7ff;
      --card:#fffaf4;
      --accent:#ff6a2a;
      --accent2:#ff9f45;
      --text:#1f2937;
      --muted:#6b7280;
      --radius:18px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family:Inter,system-ui,sans-serif;
      background:linear-gradient(120deg,var(--bg1),var(--bg2));
      color:var(--text);
    }
    .container{
      max-width:920px;
      margin:40px auto;
      padding:0 20px 80px;
    }
    .card{
      background:var(--card);
      border-radius:var(--radius);
      padding:22px;
      margin-bottom:22px;
      box-shadow:0 10px 30px rgba(0,0,0,.06);
    }
    .header{
      display:flex;
      align-items:center;
      gap:16px;
    }
    .avatar{
      width:54px;
      height:54px;
      border-radius:50%;
      background:linear-gradient(135deg,#ff6a2a,#ffb36b);
      color:#fff;
      display:flex;
      align-items:center;
      justify-content:center;
      font-weight:800;
      font-size:22px;
    }
    .subtitle{
      font-size:12px;
      color:var(--accent);
      font-weight:700;
      letter-spacing:.08em;
      text-transform:uppercase;
    }
    h1{margin:2px 0 0;font-size:26px}

    .usage{
      display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:18px;
      text-align:center;
    }
    .metric span{display:block;font-size:12px;font-weight:700}
    .metric strong{font-size:28px}

    .child{
      display:flex;
      justify-content:space-between;
      align-items:center;
      padding:14px;
      border:1px solid #eee;
      border-radius:14px;
      margin-top:12px;
    }
    .child-left{
      display:flex;
      gap:12px;
      align-items:center;
    }
    .child img{
      width:42px;
      height:42px;
      border-radius:50%;
    }
    .actions button{
      border:1px solid var(--accent);
      background:none;
      color:var(--accent);
      padding:6px 12px;
      border-radius:999px;
      font-weight:600;
      cursor:pointer;
      margin-left:6px;
    }
    .btn{
      padding:10px 18px;
      border-radius:999px;
      font-weight:700;
      cursor:pointer;
      border:1px solid var(--accent);
      background:none;
      color:var(--accent);
    }
    .btn.primary{
      background:linear-gradient(135deg,var(--accent),var(--accent2));
      color:#fff;
      border:none;
    }
    .footer-actions{
      display:flex;
      justify-content:space-between;
      margin-top:30px;
      flex-wrap:wrap;
      gap:12px;
    }
    @media(max-width:700px){
      .usage{grid-template-columns:1fr}
    }
  </style>
</head>

<body>
<div class="container">

  <!-- HEADER -->
  <div class="card header">
    <div class="avatar" id="avatar">?</div>
    <div>
      <div class="subtitle">Panel de Padres</div>
      <h1 id="welcome">Cargando…</h1>
    </div>
  </div>

  <!-- ACCOUNT -->
  <div class="card">
    <h3>Detalles de la cuenta</h3>
    <p class="muted">Estado: <strong>Activo</strong></p>
  </div>

  <!-- USAGE (placeholder, מחובר בהמשך) -->
  <div class="card">
    <h3>Uso semanal</h3>
    <div class="usage">
      <div class="metric"><span>Preguntas</span><strong>—</strong></div>
      <div class="metric"><span>Imágenes</span><strong>—</strong></div>
      <div class="metric"><span>Voz</span><strong>—</strong></div>
    </div>
  </div>

  <!-- CHILDREN -->
  <div class="card">
    <h3>Perfiles de niños</h3>
    <div id="childrenList">
      <p class="muted">Cargando perfiles…</p>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer-actions">
    <button class="btn" onclick="goHome()">← Volver al inicio</button>
    <button class="btn primary" onclick="logout()">Cerrar sesión</button>
  </div>

</div>

<script>
const SUPABASE_URL = "https://bxnfzuglfwytiyaguwjj.supabase.co";
const SUPABASE_ANON_KEY = "PASTE_YOUR_ANON_KEY_HERE";

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

function goHome(){
  window.location.href = "/";
}

async function logout(){
  await sb.auth.signOut();
  window.location.replace("/");
}

async function loadChildren(userId){
  const { data, error } = await sb
    .from("kids_profiles")
    .select("*")
    .eq("user_id", userId);

  const box = document.getElementById("childrenList");
  box.innerHTML = "";

  if (error || !data.length){
    box.innerHTML = "<p class='muted'>No hay perfiles aún</p>";
    return;
  }

  data.forEach(child=>{
    box.innerHTML += `
      <div class="child">
        <div class="child-left">
          <img src="https://i.pravatar.cc/80?u=${child.id}">
          <div>
            <strong>${child.child_name}</strong><br>
            <small class="muted">Edad ${child.age}</small>
          </div>
        </div>
        <div class="actions">
          <button>Editar</button>
          <button>Eliminar</button>
        </div>
      </div>
    `;
  });
}

(async ()=>{
  const { data:{ session } } = await sb.auth.getSession();

  if (!session){
    window.location.replace("/onboarding/cuenta/");
    return;
  }

  const user = session.user;
  const name = user.user_metadata?.full_name || "Padre";

  document.getElementById("welcome").textContent = "Bienvenido, " + name;
  document.getElementById("avatar").textContent = name.charAt(0).toUpperCase();

  loadChildren(user.id);
})();
</script>

</body>
</html>
