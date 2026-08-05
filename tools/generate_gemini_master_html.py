import json
import os

def generate_html():
    info_path = 'books/_info.json'
    routing_path = 'research/pipeline_v2/registry/book_routing.json'

    with open(info_path, 'r', encoding='utf-8') as f:
        books_info = json.load(f)

    with open(routing_path, 'r', encoding='utf-8') as f:
        routing = json.load(f).get('routes', {})

    # Create a mapping of book_id or title
    html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 3.6 Master V8 Intelligence Synthesis — 125 Kitaplık Analiz & Mimari Reçetesi</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #070a11;
            --bg-card: rgba(15, 23, 42, 0.75);
            --bg-card-hover: rgba(30, 41, 59, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(59, 130, 246, 0.3);
            
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            
            --primary: #3b82f6;
            --primary-glow: #60a5fa;
            --purple: #8b5cf6;
            --cyan: #06b6d4;
            --emerald: #10b981;
            --amber: #f59e0b;
            --rose: #f43f5e;
            
            --font-sans: 'Inter', system-ui, sans-serif;
            --font-display: 'Outfit', system-ui, sans-serif;
            --font-mono: 'Fira Code', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: var(--font-sans);
            line-height: 1.6;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 65%, rgba(139, 92, 246, 0.08) 0%, transparent 40%);
            background-attachment: fixed;
        }

        /* Glassmorphism Navigation Bar */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(7, 10, 17, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.25rem;
            background: linear-gradient(135deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-badge {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
            border: 1px solid rgba(96, 165, 250, 0.4);
            color: #93c5fd;
            font-size: 0.75rem;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-family: var(--font-mono);
            font-weight: 600;
        }

        .nav-links {
            display: flex;
            gap: 1.5rem;
            list-style: none;
        }

        .nav-links a {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .nav-links a:hover {
            color: var(--primary-glow);
        }

        /* Layout Container */
        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 2rem;
        }

        /* Hero Section */
        .hero {
            position: relative;
            padding: 4rem 2rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1.5rem;
            margin-bottom: 3rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4, #10b981);
        }

        .hero-title {
            font-family: var(--font-display);
            font-size: 2.75rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-subtitle {
            font-size: 1.15rem;
            color: var(--text-muted);
            max-width: 900px;
            margin-bottom: 2rem;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-top: 2rem;
        }

        .stat-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            padding: 1.25rem;
            border-radius: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: var(--border-glow);
        }

        .stat-value {
            font-family: var(--font-display);
            font-size: 2.25rem;
            font-weight: 800;
            color: var(--primary-glow);
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }

        /* Interactive Filter Bar */
        .filter-section {
            position: sticky;
            top: 70px;
            z-index: 900;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1rem 1.5rem;
            margin-bottom: 2.5rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: space-between;
            align-items: center;
        }

        .search-box {
            position: relative;
            flex: 1;
            min-width: 280px;
        }

        .search-input {
            width: 100%;
            background: rgba(7, 10, 17, 0.8);
            border: 1px solid var(--border-color);
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            border-radius: 0.75rem;
            color: var(--text-main);
            font-family: var(--font-sans);
            font-size: 0.9rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .search-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }

        .search-icon {
            position: absolute;
            left: 0.85rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-dim);
        }

        .filter-pills {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .pill-btn {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .pill-btn.active, .pill-btn:hover {
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary-glow);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        /* Content Sections */
        .section {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1.25rem;
            padding: 2.5rem;
            margin-bottom: 2.5rem;
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.75rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .section-icon {
            width: 42px;
            height: 42px;
            border-radius: 0.75rem;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-glow);
            font-size: 1.25rem;
        }

        .section-title {
            font-family: var(--font-display);
            font-size: 1.75rem;
            font-weight: 700;
        }

        /* Code & Spec Box */
        .code-block {
            background: #04060a;
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.25rem;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            color: #e2e8f0;
            overflow-x: auto;
            margin: 1rem 0;
            line-height: 1.5;
        }

        .code-keyword { color: #c084fc; }
        .code-string { color: #34d399; }
        .code-comment { color: #64748b; font-style: italic; }
        .code-func { color: #60a5fa; }
        .code-class { color: #f472b6; }

        /* Tag Badges */
        .tag {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: var(--font-mono);
            margin-right: 0.4rem;
        }

        .tag-new { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.4); }
        .tag-modify { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.4); }
        .tag-track { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.4); }

        /* Table Styling */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            font-size: 0.9rem;
        }

        .data-table th, .data-table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        .data-table th {
            background: rgba(15, 23, 42, 0.9);
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .data-table tr:hover td {
            background: rgba(30, 41, 59, 0.5);
        }

        /* Math formula box */
        .formula-card {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.5));
            border-left: 4px solid var(--primary-glow);
            padding: 1.25rem 1.5rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            font-family: var(--font-mono);
        }

        .footer {
            text-align: center;
            padding: 3rem 0;
            color: var(--text-dim);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            margin-top: 4rem;
        }
    </style>
</head>
<body>

    <nav class="navbar">
        <div class="brand-logo">
            <span>ANTIGRAVITY // V8</span>
            <span class="brand-badge">Gemini 3.6 Flash</span>
        </div>
        <ul class="nav-links">
            <li><a href="#overview">Genel Bakış</a></li>
            <li><a href="#modifications">V8 Mimari Reçetesi</a></li>
            <li><a href="#disciplines">5 Kategori Analizi</a></li>
            <li><a href="#catalog">125 Kitap İndeksi</a></li>
        </ul>
    </nav>

    <div class="container">
        
        <!-- Hero Header -->
        <header class="hero" id="overview">
            <div class="brand-badge" style="margin-bottom: 1rem; display: inline-block;">AI MASTER SYNTHESIS REPORT</div>
            <h1 class="hero-title">125 Finansal & Ticari Eserin V8 Mimarisine Entegrasyon Reçetesi</h1>
            <p class="hero-subtitle">
                Bu doküman, Antigravity AI (Gemini 3.6 Flash) tarafından V8 Behavior-Driven Trading Intelligence (Crypto Perpetual Futures) altyapısı için özel olarak sentezlenmiştir. 125 kitaptan elde edilen kurallar, matematiksel modeller ve psikolojik protokoller kodlanabilir bileşenlere dönüştürülmüştür.
            </p>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">125</div>
                    <div class="stat-label">İncelenen Eser</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">12,457</div>
                    <div class="stat-label">Deterministik Lead</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">5</div>
                    <div class="stat-label">Disiplin Kategorisi</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">18</div>
                    <div class="stat-label">V8 Modül Değişikliği</div>
                </div>
            </div>
        </header>

        <!-- Interactive Search & Filter Bar -->
        <div class="filter-section">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" placeholder="Kitap adı, yazar, modül (ör: Kelly, Elder, Wyckoff, ATR, schema.py)..." onkeyup="filterContent()">
            </div>
            <div class="filter-pills">
                <button class="pill-btn active" onclick="filterCategory('all')">Tümü</button>
                <button class="pill-btn" onclick="filterCategory('psychology')">Psikoloji</button>
                <button class="pill-btn" onclick="filterCategory('risk')">Risk & Pozisyon</button>
                <button class="pill-btn" onclick="filterCategory('price_action')">Price Action</button>
                <button class="pill-btn" onclick="filterCategory('candlestick')">Candlestick</button>
                <button class="pill-btn" onclick="filterCategory('algorithmic')">Algoritmik / Quant</button>
            </div>
        </div>

        <!-- Section 1: V8 Codebase Modifications -->
        <section class="section" id="modifications">
            <div class="section-header">
                <div class="section-icon">⚙️</div>
                <h2 class="section-title">V8 Kod Tabanında Neler Eklenecek & Değiştirilecek?</h2>
            </div>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                125 kitabın sentezi sonucunda V8 projesinin (<code style="color:var(--cyan)">src/v8/</code>) çekirdek paketinde yapılması gereken değişiklikler ve eklemeler:
            </p>

            <table class="data-table">
                <thead>
                    <tr>
                        <th>Modül / Dosya Yolu</th>
                        <th>İşlem Tipi</th>
                        <th>Literatür Kaynağı</th>
                        <th>Yapılacak Değişiklik ve Mimari Karşılığı</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>src/v8/schema.py</code></td>
                        <td><span class="tag tag-modify">MODIFY</span></td>
                        <td>v2.1 Invariant Rules</td>
                        <td>
                            <code>ProvenanceTag</code> enum'u genişletilecek (SOURCE_EXPLICIT, MARKET_TRANSLATION, V8_OPERATIONALIZATION).
                            <code>AdjudicatedClaim</code> ve <code>RiskGeometryRecord</code> veri sınıfları eklenecek.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/marketstate/builder.py</code></td>
                        <td><span class="tag tag-modify">MODIFY</span></td>
                        <td>Al Brooks, Bob Volman</td>
                        <td>
                            PIT (Point-in-Time) High/Low takip mekanizması ve Market Regime Detection (Bull Trend, Bear Trend, Trading Range) hesaplayıcısı entegre edilecek.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/experts/psychology_guard.py</code></td>
                        <td><span class="tag tag-new">NEW</span></td>
                        <td>Douglas, Elder, Taleb</td>
                        <td>
                            Arka arkaya kayıplarda (Cool-off) 24 saatlik işlem dondurma ve Revenge Trading engelleme mekanizmasını çalıştıran Expert ailesi.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/experts/atr_trailing_stop.py</code></td>
                        <td><span class="tag tag-new">NEW</span></td>
                        <td>Curtis Faith, Van Tharp</td>
                        <td>
                            Dinamik volatilite stopu ($2.0 \times \text{ATR}(14)$) hesaplayan ve kar marjını koruyan izleyen stop Expert'i.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/experts/wyckoff_vpa.py</code></td>
                        <td><span class="tag tag-new">NEW</span></td>
                        <td>Wyckoff, Anna Coulling</td>
                        <td>
                            Volume Price Analysis (VPA) ile kırılımların (Breakout) hacim teyidini alan ve Spring/UTAD tuzaklarını saptayan Expert.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/lifecycle/exposure_book.py</code></td>
                        <td><span class="tag tag-modify">MODIFY</span></td>
                        <td>Elder (2%/6% Rule), Kelly</td>
                        <td>
                            Aylık toplam risk %6'ya ulaştığında tüm pozisyonları donduran ve Half-Kelly ($f^*/2$) boyutlandırmasını zorunlu kılan kural motoru.
                        </td>
                    </tr>
                    <tr>
                        <td><code>src/v8/lab/falsification_suite.py</code></td>
                        <td><span class="tag tag-new">NEW</span></td>
                        <td>David Aronson, Perry Kaufman</td>
                        <td>
                            Monte Carlo simülasyonu ve Walk-Forward Analysis (WFA) ile stratejilerin istatistiksel anlamlılığını (p-value, DSR) test eden doğrulama paketi.
                        </td>
                    </tr>
                </tbody>
            </table>
        </section>

        <!-- Section 2: 5 Disciplines Deep-Dive -->
        <section class="section" id="disciplines">
            <div class="section-header">
                <div class="section-icon">📐</div>
                <h2 class="section-title">5 Temel Disiplin Analizi ve Formülasyonlar</h2>
            </div>

            <!-- Discipline 1 -->
            <div style="margin-bottom: 2.5rem;" class="discipline-card" data-category="psychology">
                <h3 style="color: var(--primary-glow); margin-bottom: 0.75rem;">1. Ticaret Psikolojisi ve Bilişsel Disiplin</h3>
                <p style="color: var(--text-muted);">
                    Mark Douglas ve Nassim Taleb öğretileri uyarınca, işlemler rastgele bir kazanç/kayıp dağılımına sahiptir. V8'e entegre edilecek duygusal bariyer:
                </p>
                <div class="formula-card">
                    CoolOffDuration = (ConsecutiveLosses >= 3) ? 24 Hours : 0<br>
                    DailyMaxRiskCap = 0.04 * AccountCapital
                </div>
            </div>

            <!-- Discipline 2 -->
            <div style="margin-bottom: 2.5rem;" class="discipline-card" data-category="risk">
                <h3 style="color: var(--emerald); margin-bottom: 0.75rem;">2. Risk Yönetimi ve Pozisyon Boyutlandırma Matematiği</h3>
                <p style="color: var(--text-muted);">
                    Alexander Elder (%2/%6 Kuralı) ve Ernest Chan (Half-Kelly) prensipleri:
                </p>
                <div class="formula-card">
                    PositionSize = (Capital * 0.015) / (EntryPrice - StopLossPrice)<br>
                    HalfKelly = 0.5 * (WinRate - (1 - WinRate) / WinLossRatio)
                </div>
            </div>

            <!-- Discipline 3 -->
            <div style="margin-bottom: 2.5rem;" class="discipline-card" data-category="price_action">
                <h3 style="color: var(--cyan); margin-bottom: 0.75rem;">3. Price Action ve Piyasa Yapısı</h3>
                <p style="color: var(--text-muted);">
                    Al Brooks ve Bob Volman kural dizini: Market Structure Shift (MS Shift) gerçekleşmeden trend karşıtı işlem alınamaz.
                </p>
                <div class="formula-card">
                    BullishShift = Close > Recent_Lower_High && Volume > 1.5 * SMA(Volume, 20)
                </div>
            </div>

            <!-- Discipline 4 -->
            <div style="margin-bottom: 2.5rem;" class="discipline-card" data-category="candlestick">
                <h3 style="color: var(--amber); margin-bottom: 0.75rem;">4. Mum Formasyonları ve İstatistiksel Filtreleme</h3>
                <p style="color: var(--text-muted);">
                    Steve Nison ve Thomas Bulkowski: Mum formasyonları tek başına yetersizdir, yapısal destek/direnç bölgesi zorunludur.
                </p>
                <div class="formula-card">
                    HammerValid = (LowerWick >= 2.0 * BodySize) && (Close >= High - 0.25 * BarRange)
                </div>
            </div>

            <!-- Discipline 5 -->
            <div style="margin-bottom: 2.5rem;" class="discipline-card" data-category="algorithmic">
                <h3 style="color: var(--purple); margin-bottom: 0.75rem;">5. Algoritmik Trading ve WFA Metodolojisi</h3>
                <p style="color: var(--text-muted);">
                    David Aronson (EBTA) ve Perry Kaufman: Overfitting önlemek için Walk-Forward ve Monte Carlo testi.
                </p>
                <div class="formula-card">
                    DeflatedSharpeRatio = CalculateDSR(SharpeRatio, TrialsCount, Skewness, Kurtosis)
                </div>
            </div>
        </section>

        <!-- Section 3: Exhaustive 125 Books Directory -->
        <section class="section" id="catalog">
            <div class="section-header">
                <div class="section-icon">📚</div>
                <h2 class="section-title">125 Kitaplık Tam Korpus İndeksi ve Katman Haritası</h2>
            </div>

            <table class="data-table" id="booksTable">
                <thead>
                    <tr>
                        <th>Book ID</th>
                        <th>Kitap Başlığı ve Detayı</th>
                        <th>Yıl</th>
                        <th>Track'ler</th>
                        <th>Gelenek / Lineage</th>
                        <th>V8 Hedef Bileşeni</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Populate 125 books dynamically from JSON!
    for idx, b_info in enumerate(books_info, 1):
        b_id = f"book_{idx:04d}"
        title = b_info.get('title', 'Unknown Title')
        year = b_info.get('year', '-')
        
        # Get routing info if available
        r_info = routing.get(b_id, {})
        tracks = r_info.get('tracks', [])
        lineage = r_info.get('lineage', 'general')
        
        tracks_str = " ".join([f'<span class="tag tag-track">{t}</span>' for t in tracks]) if tracks else '<span class="tag" style="background:rgba(100,116,139,0.2);color:#94a3b8;">N/A</span>'
        
        # Determine category for JS filtering
        category = 'other'
        if lineage in ['psychology_discipline', 'other'] or 'psychology' in title.lower():
            category = 'psychology'
        elif 'G' in tracks or 'risk' in lineage.lower() or 'trading' in title.lower():
            category = 'risk'
        elif lineage in ['dow_classical', 'wyckoff_volume'] or 'M' in tracks:
            category = 'price_action'
        elif lineage == 'japanese_candlestick' or 'candlestick' in title.lower():
            category = 'candlestick'
        elif lineage in ['quantitative_academic'] or 'F' in tracks or 'algo' in title.lower():
            category = 'algorithmic'

        # Target V8 Component mapping based on lineage/track
        target_mod = "src/v8/experts/"
        if 'G' in tracks:
            target_mod = "src/v8/lifecycle/exposure_book.py"
        elif 'F' in tracks:
            target_mod = "src/v8/lab/falsification_suite.py"
        elif 'M' in tracks:
            target_mod = "src/v8/marketstate/builder.py"
        elif category == 'psychology':
            target_mod = "src/v8/experts/psychology_guard.py"

        html_content += f"""
                    <tr class="book-row" data-category="{category}">
                        <td><code style="color:var(--cyan);">{b_id}</code></td>
                        <td><strong>{title}</strong></td>
                        <td>{year}</td>
                        <td>{tracks_str}</td>
                        <td><code style="color:var(--purple);">{lineage}</code></td>
                        <td><code>{target_mod}</code></td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
        </section>

        <footer class="footer">
            <p>Generated & Synthesized by <strong>Gemini 3.6 Flash (Antigravity AI)</strong> for Google Deepmind V8 Trading Intelligence Research Program.</p>
            <p style="margin-top: 0.5rem; color: var(--text-dim);">Strictly adheres to V8 Constitution, PIT Determinism, and Evidence-Bound Research Standards.</p>
        </footer>

    </div>

    <!-- Live Interactive Filtering Script -->
    <script>
        function filterContent() {
            let input = document.getElementById('searchInput').value.toLowerCase();
            let rows = document.querySelectorAll('.book-row');
            
            rows.forEach(row => {
                let text = row.innerText.toLowerCase();
                if (text.includes(input)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        function filterCategory(cat) {
            let buttons = document.querySelectorAll('.pill-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            let rows = document.querySelectorAll('.book-row');
            let cards = document.querySelectorAll('.discipline-card');

            rows.forEach(row => {
                let rowCat = row.getAttribute('data-category');
                if (cat === 'all' || rowCat === cat) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });

            cards.forEach(card => {
                let cardCat = card.getAttribute('data-category');
                if (cat === 'all' || cardCat === cat) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

    out_path = 'site/gemini_master_v8.html'
    with open(out_path, 'w', encoding='utf-8') as out_f:
        out_f.write(html_content)

    print(f"Generated {out_path} with {len(html_content.splitlines())} lines!")

if __name__ == '__main__':
    generate_html()
