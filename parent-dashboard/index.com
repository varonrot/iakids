<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Educational Activities for Kids | Askie</title>

<style>
:root{
  --bg1:#fff6ec;
  --bg2:#eef7f7;
  --card:#ffffff;
  --accent:#ff6a3d;
  --accent-soft:#ffe1d6;
  --text:#1f2937;
  --muted:#6b7280;
  --radius:18px;
}

*{box-sizing:border-box}
body{
  margin:0;
  font-family: Inter, system-ui, sans-serif;
  color:var(--text);
  background:linear-gradient(120deg,var(--bg1),var(--bg2));
}

.container{
  max-width:1100px;
  margin:auto;
  padding:60px 20px;
}

/* HERO */
.hero{
  text-align:center;
  margin-bottom:70px;
}
.hero h1{
  font-size:42px;
  line-height:1.15;
  margin-bottom:16px;
}
.hero p{
  font-size:18px;
  color:var(--muted);
  max-width:680px;
  margin:0 auto 30px;
}
.hero .badges{
  display:flex;
  gap:10px;
  justify-content:center;
  flex-wrap:wrap;
}
.badge{
  background:var(--accent-soft);
  color:var(--accent);
  padding:8px 14px;
  border-radius:999px;
  font-weight:600;
  font-size:14px;
}

/* GRID */
.grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:22px;
  margin-bottom:70px;
}

/* CARD */
.card{
  background:var(--card);
  border-radius:var(--radius);
  padding:26px 22px;
  box-shadow:0 10px 30px rgba(0,0,0,.06);
  transition:.25s ease;
}
.card:hover{
  transform:translateY(-6px);
  box-shadow:0 18px 40px rgba(0,0,0,.1);
}
.card .icon{
  font-size:34px;
  margin-bottom:14px;
}
.card h3{
  margin:0 0 10px;
  font-size:20px;
}
.card p{
  color:var(--muted);
  font-size:15px;
  line-height:1.6;
}

/* CTA */
.cta{
  background:linear-gradient(135deg,#ff6a3d,#ff915f);
  color:#fff;
  border-radius:22px;
  padding:50px 30px;
  text-align:center;
}
.cta h2{
  font-size:32px;
  margin-bottom:12px;
}
.cta p{
  font-size:17px;
  opacity:.95;
  margin-bottom:26px;
}
.cta button{
  background:#fff;
  color:var(--accent);
  border:none;
  font-size:16px;
  padding:14px 26px;
  border-radius:999px;
  font-weight:700;
  cursor:pointer;
}
.cta button:hover{
  opacity:.9;
}
</style>
</head>

<body>

<div class="container">

  <!-- HERO -->
  <section class="hero">
    <h1>Educational Activities Powered by AI</h1>
    <p>
      Safe, engaging and age-appropriate activities that help children learn,
      create and explore with the guidance of artificial intelligence.
    </p>

    <div class="badges">
      <span class="badge">Ages 3–15</span>
      <span class="badge">Parent Approved</span>
      <span class="badge">Personalized Learning</span>
    </div>
  </section>

  <!-- ACTIVITIES -->
  <section class="grid">

    <div class="card">
      <div class="icon">🔬</div>
      <h3>Science & Discovery</h3>
      <p>
        Explore nature, experiments and scientific ideas through safe,
        interactive AI-guided activities.
      </p>
    </div>

    <div class="card">
      <div class="icon">🧮</div>
      <h3>Math & Logic</h3>
      <p>
        Fun challenges that build problem-solving, number sense and logical
        thinking.
      </p>
    </div>

    <div class="card">
      <div class="icon">📚</div>
      <h3>Language & Reading</h3>
      <p>
        Story creation, vocabulary games and reading comprehension activities.
      </p>
    </div>

    <div class="card">
      <div class="icon">🎨</div>
      <h3>Art & Creativity</h3>
      <p>
        Create drawings, stories and imaginative projects together with AI.
      </p>
    </div>

    <div class="card">
      <div class="icon">💻</div>
      <h3>Coding & Technology</h3>
      <p>
        A gentle introduction to technology, logic and digital thinking.
      </p>
    </div>

  </section>

  <!-- CTA -->
  <section class="cta">
    <h2>Start Your Child’s Learning Adventure</h2>
    <p>
      Join thousands of families using Askie for safe and inspiring AI learning.
    </p>
    <button onclick="location.href='/dashboard'">
      Get Started
    </button>
  </section>

</div>

</body>
</html>
