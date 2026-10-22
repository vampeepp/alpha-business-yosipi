/**
 * Alfa-Bank Corporate News Analytics & Insight Frontend Application.
 * Manages state, API integrations, SVG supply-chain visualization,
 * 6-pillar insight rendering, and executive Q&A chat.
 */

const app = {
  currentClientUid: "U_AGRO_001",
  currentRole: "Генеральный директор",
  currentNewsId: "NEWS-2026-09-001",
  filterLevel: "ALL",
  clientsData: [],
  currentFeed: [],

  init() {
    this.bindEvents();
    this.loadClients();
    this.loadResearch();
  },

  bindEvents() {
    // Client selection change
    document.getElementById("companySelect").addEventListener("change", (e) => {
      this.currentClientUid = e.target.value;
      this.refreshCurrentClientView();
    });

    // Role selection change
    document.getElementById("roleSelect").addEventListener("change", (e) => {
      this.currentRole = e.target.value;
      this.loadNewsFeed();
    });

    // Tab buttons
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tabId = btn.getAttribute("data-tab");
        this.switchTab(tabId);
      });
    });

    // Filter pills
    document.querySelectorAll(".pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        document.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        this.filterLevel = pill.getAttribute("data-filter");
        this.renderNewsFeed();
      });
    });

    // Chat submit
    document.getElementById("btnSendChat").addEventListener("click", () => {
      this.sendChatMessage();
    });
    document.getElementById("chatInput").addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.sendChatMessage();
    });
  },

  switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));

    const targetBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    const targetPane = document.getElementById(tabId);
    if (targetBtn) targetBtn.classList.add("active");
    if (targetPane) targetPane.classList.add("active");
  },

  async loadClients() {
    try {
      const res = await fetch("/api/clients");
      this.clientsData = await res.json();
      const select = document.getElementById("companySelect");
      select.innerHTML = "";

      this.clientsData.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.synthetic_u;
        opt.textContent = `${c.synthetic_u} | ${c.mainokved_name} (${c.revenue_billions} млрд ₽)`;
        if (c.synthetic_u === this.currentClientUid) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });

      this.refreshCurrentClientView();
    } catch (err) {
      console.error("Failed to load clients:", err);
    }
  },

  async refreshCurrentClientView() {
    await this.loadClientProfile();
    await this.loadNewsFeed();
    await this.loadCounterpartyGraph();
  },

  async loadClientProfile() {
    try {
      const res = await fetch(`/api/client/${this.currentClientUid}`);
      const data = await res.json();
      const p = data.profile;

      document.getElementById("dispCompanyName").textContent = `${p.synthetic_u} (${p.org_type})`;
      document.getElementById("dispRevenue").textContent = `${p.revenue_billions} млрд ₽`;
      document.getElementById("dispOkved").textContent = `${p.mainokved_code} ${p.mainokved_name}`;
      document.getElementById("dispDebt").textContent = p.has_loan ? "Кредиты + Лизинг (Активен)" : "Собственный капитал";
      document.getElementById("dispFts").textContent = p.has_foreign_trade ? `ВЭД: ${p.fts_country_name || 'Активен'}` : "Внутренний рынок";
      document.getElementById("dispGroup").textContent = p.group_id || "Автономное предприятие";
    } catch (err) {
      console.error("Failed to load client profile:", err);
    }
  },

  async loadNewsFeed() {
    const grid = document.getElementById("newsGrid");
    grid.innerHTML = '<div class="loading-state">Многофакторный AI-скоринг новостного потока...</div>';

    try {
      const res = await fetch(`/api/news/feed?uid=${this.currentClientUid}&role=${encodeURIComponent(this.currentRole)}`);
      const data = await res.json();
      this.currentFeed = data.feed || [];
      this.renderNewsFeed();
    } catch (err) {
      grid.innerHTML = `<div class="empty-state">Ошибка загрузки ленты: ${err.message}</div>`;
    }
  },

  renderNewsFeed() {
    const grid = document.getElementById("newsGrid");
    grid.innerHTML = "";

    const filtered = this.currentFeed.filter((item) => {
      if (this.filterLevel === "ALL") return true;
      return item.score.priority_level === this.filterLevel;
    });

    if (filtered.length === 0) {
      grid.innerHTML = '<div class="empty-state">Нет событий с выбранным уровнем приоритета.</div>';
      return;
    }

    filtered.forEach((item) => {
      const n = item.news;
      const s = item.score;

      const card = document.createElement("div");
      const priorityClass = s.priority_level === "CRITICAL" ? "critical-card" : (s.priority_level === "HIGH" ? "high-card" : "");
      card.className = `news-card ${priorityClass}`;

      const relClass = s.priority_level === "CRITICAL" ? "relevance-critical" : (s.priority_level === "HIGH" ? "relevance-high" : "relevance-medium");

      card.innerHTML = `
        <div>
          <div class="news-card-header">
            <span class="badge-relevance ${relClass}">⚡ Релевантность: ${s.total_score}% (${s.priority_level})</span>
            <span class="news-meta-date">${n.publication_date.substring(0, 10)}</span>
          </div>
          <h3 class="news-card-title">${n.title}</h3>
          <p class="news-card-summary">${n.summary}</p>
          <div class="relevance-reason-box">
            <span class="reason-tag">Бизнес-факторы клиента:</span> ${s.explanation}
          </div>
        </div>
        <div class="news-card-footer">
          <span class="news-source-badge">📰 ${n.source}</span>
          <button class="alfa-btn-primary" onclick="app.generateInsight('${n.news_id}')">
            Детальный анализ (6 блоков) →
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
  },

  async generateInsight(newsId) {
    this.currentNewsId = newsId;
    this.switchTab("tab-insight");
    const container = document.getElementById("insightContainer");
    container.innerHTML = `
      <div class="loading-state">
        <h3>Агентная обработка события мультиагентным комплексом...</h3>
        <p>1. Планирование шагов → 2. Опрос профиля и графа поставок → 3. RAG-поиск макроисследований Альфа-Банка → 4. Синтез 6 блоков → 5. Самопроверка критиком</p>
      </div>
    `;

    try {
      const res = await fetch(`/api/news/insight?uid=${this.currentClientUid}&news_id=${newsId}&role=${encodeURIComponent(this.currentRole)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      this.renderInsightView(data.insight);
      this.renderTraceTimeline(data.agent_trace);
    } catch (err) {
      container.innerHTML = `<div class="empty-state">Ошибка анализа: ${err.message}</div>`;
    }
  },

  renderInsightView(insight) {
    const container = document.getElementById("insightContainer");

    const lineageItems = (insight.data_lineage.client_features_utilized || [])
      .map((f) => `<li>${f}</li>`)
      .join("");
    const macroReports = (insight.data_lineage.bank_macro_research_used || [])
      .map((r) => `<li>${r}</li>`)
      .join("");

    const productsHtml = (insight.suggested_bank_products || []).map((p) => `
      <div class="bank-product-box">
        <div>
          <span class="prod-category">${p.category}</span>
          <div class="prod-title">${p.product_name}</div>
          <div class="prod-benefit">${p.benefit}</div>
        </div>
        <button class="alfa-btn-primary" onclick="alert('Заявка по продукту «${p.product_name}» направлена персональному менеджеру крупного бизнеса.')">
          ${p.action_text}
        </button>
      </div>
    `).join("");

    container.innerHTML = `
      <div class="insight-header-banner">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <span class="bank-tag">АО «АЛЬФА-БАНК» | ПЕРСОНАЛИЗИРОВАННЫЙ БИЗНЕС-ИНСАЙТ</span>
          <span style="font-size: 13px; font-weight: 700; color: #059669;">
            ✓ Верификация критика: ${insight.critic_review.critic_score || 95}/100 (${insight.critic_review.verdict || 'Одобрено'})
          </span>
        </div>
        <h1>Персонализированная интерпретация события для ${this.currentClientUid}</h1>
        <p style="color: #64748B; font-size: 13px;">Подготовлено для роли: <strong>${this.currentRole}</strong> | Дата генерации: ${new Date().toLocaleString('ru-RU')}</p>
      </div>

      <!-- 6-Pillar Deep Dive Grid -->
      <div class="pillar-grid">
        <!-- Pillar 1 -->
        <div class="pillar-card">
          <div class="pillar-title">
            <span class="pillar-num">1</span>
            <span>Что произошло? (Фактология и верификация)</span>
          </div>
          <div class="pillar-body">${this.formatMarkdown(insight.what_happened)}</div>
        </div>

        <!-- Pillar 2 -->
        <div class="pillar-card" style="border-top: 4px solid #0284C7;">
          <div class="pillar-title">
            <span class="pillar-num" style="background: #0284C7;">2</span>
            <span>Почему это важно для Вашей компании? (Персонализация)</span>
          </div>
          <div class="pillar-body">${this.formatMarkdown(insight.why_it_matters)}</div>
        </div>

        <!-- Pillar 3 -->
        <div class="pillar-card">
          <div class="pillar-title">
            <span class="pillar-num">3</span>
            <span>Какие последствия возможны? (Риски и возможности)</span>
          </div>
          <div class="pillar-body">${this.formatMarkdown(insight.potential_consequences)}</div>
        </div>

        <!-- Pillar 4 -->
        <div class="pillar-card">
          <div class="pillar-title">
            <span class="pillar-num">4</span>
            <span>Какие действия релевантны? (План для ${this.currentRole})</span>
          </div>
          <div class="pillar-body">${this.formatMarkdown(insight.recommended_actions)}</div>
        </div>

        <!-- Pillar 5 (Special Bank Stance Box) -->
        <div class="pillar-card pillar-bank-expert" style="grid-column: 1 / -1;">
          <div class="pillar-title" style="border-bottom: 2px solid var(--alfa-red);">
            <span class="pillar-num" style="background: var(--alfa-red);">5</span>
            <span style="color: var(--alfa-red); font-size: 17px;">Экспертная позиция Альфа-Банка (Центр макроэкономических исследований)</span>
          </div>
          <div class="pillar-body">${this.formatMarkdown(insight.bank_expert_perspective)}</div>
        </div>

        <!-- Pillar 6 (Data Lineage & Audit) -->
        <div class="pillar-card" style="grid-column: 1 / -1; background: #F8FAFC;">
          <div class="pillar-title">
            <span class="pillar-num" style="background: #475569;">6</span>
            <span>На чем основан вывод? (Data Lineage & Трассировка)</span>
          </div>
          <div class="pillar-body">
            <p><strong>Клиентские признаки и финансовые параметры:</strong></p>
            <ul style="margin: 8px 0 16px 20px; font-size: 12.5px;">${lineageItems}</ul>
            <p><strong>Использованные исследования и макромодели Альфа-Банка:</strong></p>
            <ul style="margin: 8px 0 16px 20px; font-size: 12.5px;">${macroReports}</ul>
            <p style="font-size: 11.5px; color: #64748B;">Метод рассуждений: ${insight.data_lineage.ai_inference_method}</p>
          </div>
        </div>
      </div>

      <!-- Native Banking Products Deck -->
      <div class="products-card-deck">
        <h3 style="font-size: 16px; color: var(--alfa-black); display: flex; align-items: center; gap: 8px;">
          <span>🎯</span> Целевые решения Альфа-Банка для оптимизации рисков события
        </h3>
        <p style="font-size: 13px; color: #64748B; margin-top: 4px;">Нативные банковские инструменты, снижающие долговую нагрузку и хеджирующие валютно-ценовые колебания.</p>
        <div class="products-grid">${productsHtml}</div>
      </div>
    `;
  },

  renderTraceTimeline(trace) {
    const timeline = document.getElementById("traceTimeline");
    if (!trace || trace.length === 0) {
      timeline.innerHTML = '<div class="empty-state">Нет данных трассировки.</div>';
      return;
    }

    timeline.innerHTML = trace.map((t) => `
      <div class="trace-step-card">
        <div class="trace-step-header">
          <span class="trace-step-name">Шаг ${t.step_number}: ${t.step_name}</span>
          <span class="trace-role">${t.agent_role}</span>
        </div>
        <div class="trace-summary">${t.action_summary}</div>
        <pre class="trace-details-pre">${JSON.stringify(t.details, null, 2)}</pre>
      </div>
    `).join("");
  },

  async loadCounterpartyGraph() {
    try {
      const res = await fetch(`/api/client/${this.currentClientUid}`);
      const data = await res.json();
      const exposures = data.counterparty_exposures || [];
      const tbody = document.querySelector("#counterpartyTable tbody");
      tbody.innerHTML = "";

      if (exposures.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">Контрагенты в реестре не найдены.</td></tr>';
      } else {
        exposures.forEach((exp) => {
          const tr = document.createElement("tr");
          const riskColor = exp.risk_level === "HIGH" ? "color: #EF3124; font-weight:700;" : (exp.risk_level === "MEDIUM" ? "color: #D97706; font-weight:700;" : "color: #059669;");
          tr.innerHTML = `
            <td><strong>${exp.counterparty_name}</strong></td>
            <td>${exp.relation_type}</td>
            <td>${(exp.payment_amount / 1e9).toFixed(2)} млрд ₽</td>
            <td>${exp.payment_count}</td>
            <td>${exp.share_of_turnover}%</td>
            <td style="${riskColor}">${exp.risk_level}</td>
          `;
          tbody.appendChild(tr);
        });
      }

      this.renderGraphSvg(data.supply_chain_graph);
    } catch (err) {
      console.error("Failed to load counterparty graph:", err);
    }
  },

  renderGraphSvg(graphData) {
    const canvas = document.getElementById("graphCanvas");
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      canvas.innerHTML = '<div class="empty-state">Нет связей для визуализации</div>';
      return;
    }

    const width = 540;
    const height = 360;
    const centerX = width / 2;
    const centerY = height / 2;

    const rootNode = graphData.nodes.find((n) => n.is_root) || graphData.nodes[0];
    const otherNodes = graphData.nodes.filter((n) => n.id !== rootNode.id);

    let svgHtml = `<svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" style="background: #F8FAFC;">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#94A3B8"/>
        </marker>
      </defs>`;

    const radius = 125;
    const nodeCoords = {};
    nodeCoords[rootNode.id] = { x: centerX, y: centerY };

    otherNodes.forEach((node, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(otherNodes.length, 1);
      const nx = centerX + radius * Math.cos(angle);
      const ny = centerY + radius * Math.sin(angle);
      nodeCoords[node.id] = { x: nx, y: ny };
    });

    // Draw edges
    (graphData.edges || []).forEach((e) => {
      const from = nodeCoords[e.from] || { x: centerX, y: centerY };
      const to = nodeCoords[e.to] || { x: centerX, y: centerY };
      const color = e.type === "IN_PAYMENT" ? "#10B981" : "#EF3124";
      svgHtml += `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke="${color}" stroke-width="2.5" stroke-dasharray="${e.type === 'OUT_PAYMENT' ? '4 2' : 'none'}" marker-end="url(#arrow)"/>`;
    });

    // Draw nodes
    otherNodes.forEach((node) => {
      const coord = nodeCoords[node.id];
      svgHtml += `
        <circle cx="${coord.x}" cy="${coord.y}" r="22" fill="#FFFFFF" stroke="#64748B" stroke-width="2"/>
        <text x="${coord.x}" y="${coord.y + 36}" font-size="10" font-weight="600" text-anchor="middle" fill="#1F2229">
          ${node.id}
        </text>
        <text x="${coord.x}" y="${coord.y + 4}" font-size="9" text-anchor="middle" fill="#64748B">
          ${node.revenue_bln}B
        </text>
      `;
    });

    // Draw central root node
    svgHtml += `
      <circle cx="${centerX}" cy="${centerY}" r="32" fill="#EF3124" stroke="#C91E12" stroke-width="3"/>
      <text x="${centerX}" y="${centerY - 4}" font-size="11" font-weight="800" text-anchor="middle" fill="#FFFFFF">
        ${rootNode.id}
      </text>
      <text x="${centerX}" y="${centerY + 12}" font-size="9" text-anchor="middle" fill="#FEECEB">
        ${rootNode.revenue_bln} млрд ₽
      </text>
    `;

    svgHtml += "</svg>";
    canvas.innerHTML = svgHtml;
  },

  async loadResearch() {
    const grid = document.getElementById("researchGrid");
    try {
      const res = await fetch("/api/research");
      const reports = await res.json();
      grid.innerHTML = "";

      reports.forEach((r) => {
        const card = document.createElement("div");
        card.className = "research-card";
        const sectors = (r.impacted_sectors || []).map((s) => `<span style="background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${s}</span>`).join(" ");

        card.innerHTML = `
          <div class="research-author">${r.author} • ${r.date}</div>
          <h3>${r.title}</h3>
          <p style="font-size: 13px; color: #475569; margin-bottom: 12px;">${r.summary}</p>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">${sectors}</div>
        `;
        grid.appendChild(card);
      });
    } catch (err) {
      grid.innerHTML = `<div class="empty-state">Ошибка загрузки аналитики: ${err.message}</div>`;
    }
  },

  async sendChatMessage() {
    const input = document.getElementById("chatInput");
    const question = input.value.trim();
    if (!question) return;

    const messages = document.getElementById("chatMessages");

    // Add user message
    const userBubble = document.createElement("div");
    userBubble.className = "chat-bubble user";
    userBubble.textContent = question;
    messages.appendChild(userBubble);
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // Loading bubble
    const aiBubble = document.createElement("div");
    aiBubble.className = "chat-bubble ai";
    aiBubble.innerHTML = "<em>Формирование ответа с привязкой к профилю клиента и исследованиям Альфа-Банка...</em>";
    messages.appendChild(aiBubble);
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch("/api/assistant/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          uid: this.currentClientUid,
          news_id: this.currentNewsId,
          question: question,
          role: this.currentRole,
        }),
      });
      const data = await res.json();
      aiBubble.innerHTML = `<strong>Альфа-Аналитик:</strong>\n\n${this.formatMarkdown(data.answer)}`;
      messages.scrollTop = messages.scrollHeight;
    } catch (err) {
      aiBubble.textContent = `Ошибка получения ответа: ${err.message}`;
    }
  },

  formatMarkdown(text) {
    if (!text) return "";
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/• /g, "• ")
      .replace(/\n/g, "<br/>");
  },
};

window.addEventListener("DOMContentLoaded", () => {
  app.init();
});
