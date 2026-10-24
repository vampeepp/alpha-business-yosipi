/**
 * Alfa-Online Corporate News Analytics Front-end Controller
 * Matches the native Alfa-Bank Online mobile & web app interface.
 */

const app = {
  currentClientUid: "U_AGRO_001",
  currentRole: "Генеральный директор",
  currentFeed: [],
  currentNewsId: "NEWS-2026-09-001",
  filterLevel: "ALL",
  allClients: [],

  async init() {
    await this.loadClients();
    this.setupListeners();
  },

  setupListeners() {
    // Top dock tabs
    document.querySelectorAll(".dock-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        if (tab) this.switchTab(tab);
      });
    });
  },

  async loadClients() {
    try {
      const res = await fetch("/api/clients");
      this.allClients = await res.json();

      const modalSelect = document.getElementById("modalCompanySelect");
      if (modalSelect) {
        modalSelect.innerHTML = "";
        this.allClients.forEach((c) => {
          const opt = document.createElement("option");
          opt.value = c.synthetic_u;
          opt.textContent = `${c.synthetic_u} | ${c.mainokved_name} (${c.revenue_billions} млрд ₽)`;
          if (c.synthetic_u === this.currentClientUid) opt.selected = true;
          modalSelect.appendChild(opt);
        });
      }

      await this.refreshCurrentClientView();
    } catch (err) {
      console.error("Failed to load clients:", err);
    }
  },

  async refreshCurrentClientView() {
    await this.loadClientProfile();
    await this.loadNewsFeed();
    await this.loadCounterpartyGraph();
    await this.loadResearch();
  },

  async loadClientProfile() {
    try {
      const res = await fetch(`/api/client/${this.currentClientUid}`);
      const data = await res.json();
      const p = data.profile;

      // Update Top Bar & Sidebar
      const topName = document.getElementById("topCompanyName");
      const topRole = document.getElementById("topRoleName");
      if (topName) topName.textContent = `${p.synthetic_u} (${p.org_type})`;
      if (topRole) topRole.textContent = this.currentRole;

      const revVal = document.getElementById("dispRevenueVal");
      if (revVal) revVal.textContent = `${p.revenue_billions} млрд ₽`;

      const okvedShort = document.getElementById("dispOkvedShort");
      if (okvedShort) okvedShort.textContent = `${p.mainokved_code} ${p.mainokved_name}`;

      const groupShort = document.getElementById("dispGroupShort");
      if (groupShort) groupShort.textContent = p.group_id || "Автономное предприятие";

      const loanVal = document.getElementById("dispLoanVal");
      if (loanVal) loanVal.textContent = p.has_loan ? `${(p.revenue_billions * 0.28).toFixed(2)} млрд ₽` : "0,00 ₽";

      const leasingVal = document.getElementById("dispLeasingVal");
      if (leasingVal) leasingVal.textContent = p.has_leasing ? `${(p.revenue_billions * 0.1).toFixed(2)} млрд ₽` : "0,00 ₽";

      const vedBadge = document.getElementById("dispVedBadge");
      const vedStatus = document.getElementById("dispVedStatus");
      if (vedBadge && vedStatus) {
        if (p.has_foreign_trade) {
          vedBadge.textContent = p.fts_country_name || "ВЭД Активен";
          vedStatus.textContent = "Прямой валютный контракт";
        } else {
          vedBadge.textContent = "Внутренний рынок";
          vedStatus.textContent = "Без трансграничных платежей";
        }
      }
    } catch (err) {
      console.error("Failed to load client profile:", err);
    }
  },

  async loadNewsFeed() {
    const list = document.getElementById("newsFeedList");
    if (!list) return;
    list.innerHTML = '<div class="loading-spinner-box">Многофакторный AI-скоринг новостного потока...</div>';

    try {
      const res = await fetch(`/api/news/feed?uid=${this.currentClientUid}&role=${encodeURIComponent(this.currentRole)}`);
      const data = await res.json();
      this.currentFeed = data.feed || [];
      this.renderNewsFeed(this.currentFeed);
    } catch (err) {
      list.innerHTML = `<div class="loading-spinner-box">Ошибка загрузки ленты: ${err.message}</div>`;
    }
  },

  renderNewsFeed(feedItems) {
    const list = document.getElementById("newsFeedList");
    if (!list) return;
    list.innerHTML = "";

    const filtered = feedItems.filter((item) => {
      if (this.filterLevel === "ALL") return true;
      return item.score.priority_level === this.filterLevel;
    });

    if (filtered.length === 0) {
      list.innerHTML = '<div class="loading-spinner-box">Нет событий с выбранным уровнем приоритета.</div>';
      return;
    }

    filtered.forEach((item) => {
      const n = item.news;
      const s = item.score;

      const card = document.createElement("div");
      card.className = "news-item-card";
      card.onclick = () => this.openDetailSheet(n.news_id);

      const scoreClass = s.priority_level === "CRITICAL" ? "score-critical" : "score-high";
      const clusterCount = (n.cross_verification_sources || []).length || 2;
      const novelty = n.novelty_score || 95;
      
      // Risk / Opportunity tags (Item 6)
      const isRisk = n.sentiment.includes("NEGATIVE") || n.sentiment.includes("HAWKISH") || s.total_score >= 60;
      const roBadge = isRisk 
        ? `<span style="font-size: 9px; font-weight: 800; color: #F87171; background: rgba(239, 49, 36, 0.15); border: 1px solid rgba(239, 49, 36, 0.3); padding: 2px 6px; border-radius: 4px;">РИСК (margin, liquidity)</span>`
        : `<span style="font-size: 9px; font-weight: 800; color: #34D399; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px;">ВОЗМОЖНОСТЬ (capex, revenue)</span>`;

      // Event cluster badge (Item 5)
      const clusterBadge = `<span style="font-size: 9px; font-weight: 700; color: #38BDF8; background: rgba(56, 189, 248, 0.12); padding: 2px 6px; border-radius: 4px;">СОБЫТИЕ • Источников: ${clusterCount}</span>`;

      // Counterparty Alert if applicable (Item 2)
      let counterpartyPill = "";
      if (s.counterparty_supply_chain_score > 0) {
        counterpartyPill = `<div style="font-size: 10.5px; font-weight: 700; color: #FBBF24; background: rgba(245, 158, 11, 0.1); border-left: 3px solid #F59E0B; padding: 4px 8px; border-radius: 4px;">Связанный риск по цепочке B2B-контрагентов (+${s.counterparty_supply_chain_score} pts)</div>`;
      }

      // Personalized relevance reason (Item 4)
      const reasonPill = `<div style="font-size: 11px; color: var(--text-gray); background: rgba(255, 255, 255, 0.03); border-left: 3px solid #EF3124; padding: 4px 8px; border-radius: 4px;"><strong>Персональная причина:</strong> ${s.explanation}</div>`;

      card.innerHTML = `
        <div class="news-item-top">
          <span class="news-category-tag">${n.category} • ${n.publication_date.substring(0, 10)}</span>
          <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
            ${clusterBadge}
            ${roBadge}
            <span class="news-score-badge ${scoreClass}">${s.total_score}% (${s.priority_level})</span>
          </div>
        </div>
        <h4 class="news-item-title">${n.title}</h4>
        <p class="news-item-summary">${n.summary}</p>
        ${counterpartyPill}
        ${reasonPill}
        <div class="news-item-footer">
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="news-source-label">${n.source}</span>
            <span style="font-size: 10px; color: var(--text-dim);">Новизна: ${novelty}%</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button onclick="event.stopPropagation(); app.sendFeedback('thumbs_up', '${n.news_id}')" style="background: transparent; border: none; cursor: pointer; color: var(--text-dim); display: inline-flex; align-items: center;" title="Полезно">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
            </button>
            <button onclick="event.stopPropagation(); app.sendFeedback('thumbs_down', '${n.news_id}')" style="background: transparent; border: none; cursor: pointer; color: var(--text-dim); display: inline-flex; align-items: center;" title="Нерелевантно">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg>
            </button>
            <span class="open-insight-link">6 блоков & Каузальная цепочка &rarr;</span>
          </div>
        </div>
      `;
      list.appendChild(card);
    });

    // Also populate favorites tab
    const favList = document.getElementById("favoritesList");
    if (favList) {
      const topItems = feedItems.filter((i) => i.score.total_score >= 80);
      favList.innerHTML = "";
      topItems.forEach((item) => {
        const n = item.news;
        const c = document.createElement("div");
        c.className = "news-item-card";
        c.onclick = () => this.openDetailSheet(n.news_id);
        c.innerHTML = `
          <div class="news-item-top">
            <span class="news-category-tag">Приоритет Совета Директоров</span>
            <span class="news-score-badge score-critical">${item.score.total_score}%</span>
          </div>
          <h4 class="news-item-title">${n.title}</h4>
          <p class="news-item-summary">${n.summary}</p>
        `;
        favList.appendChild(c);
      });
    }
  },

  // CHATGPT-STYLE AI COPILOT CONTROLLERS
  escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  },

  resetChatgptThread() {
    const hist = document.getElementById("chatgptHistoryContainer");
    if (hist) hist.innerHTML = "";
    
    const thread = document.getElementById("chatgptThread");
    if (thread) thread.style.display = "none";

    const respMsg = document.getElementById("chatgptActiveResponseMsg");
    if (respMsg) respMsg.style.display = "none";

    const input = document.getElementById("aiHubInput");
    if (input) input.value = "";
  },

  async askQuickCopilot(promptText) {
    const input = document.getElementById("aiHubInput");
    if (input) input.value = promptText;
    await this.handleHubSubmit();
  },

  async handleHubSubmit() {
    const input = document.getElementById("aiHubInput");
    const q = input ? input.value.trim() : "";
    if (!q) return;

    // Show thread on submit
    const thread = document.getElementById("chatgptThread");
    if (thread) thread.style.display = "flex";

    // Append user message bubble to ChatGPT thread
    const hist = document.getElementById("chatgptHistoryContainer");
    if (hist) {
      const uMsg = document.createElement("div");
      uMsg.className = "chatgpt-msg user";
      uMsg.innerHTML = `<div class="chatgpt-user-bubble">${this.escapeHtml(q)}</div>`;
      hist.appendChild(uMsg);
    }
    if (input) input.value = "";

    const factEl = document.getElementById("hubFactText");
    const alfaEl = document.getElementById("hubAlfaText");
    const aiEl = document.getElementById("hubAiText");
    const flowEl = document.getElementById("hubChainFlow");
    const evidenceEl = document.getElementById("hubEvidencePills");
    const chainRow = document.getElementById("hubChainRow");
    const evidenceRow = document.getElementById("hubEvidenceRow");
    const respMsg = document.getElementById("chatgptActiveResponseMsg");

    if (respMsg) respMsg.style.display = "flex";
    if (aiEl) aiEl.innerHTML = "<em>Генерация аналитического вывода и расчет каузальной цепочки...</em>";
    if (factEl) factEl.textContent = "Анализ макроэкономических данных и позиции ЦБ РФ...";
    if (alfaEl) alfaEl.textContent = "Поиск профильных исследований ЦМИ Альфа-Банка...";

    if (thread) thread.scrollTop = thread.scrollHeight;

    try {
      const res = await fetch("/api/assistant/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          uid: this.currentClientUid,
          news_id: this.currentNewsId,
          question: q,
          role: this.currentRole,
        }),
      });
      const data = await res.json();

      if (factEl) factEl.textContent = data.fact_statement || "Фактические данные согласованы с открытыми источниками.";
      if (alfaEl) alfaEl.textContent = data.alfa_view || "Центр макроэкономических исследований Альфа-Банка рекомендует консервативную стратегию.";
      if (aiEl) aiEl.innerHTML = this.formatMarkdown(data.ai_view || data.answer);

      if (flowEl && data.impact_chain_summary) {
        if (chainRow) chainRow.style.display = "flex";
        const steps = data.impact_chain_summary.split(/➔|->|&rarr;/).map(s => s.trim());
        flowEl.innerHTML = steps.map((s, idx) => {
          const cls = idx === steps.length - 1 ? "success" : (idx >= 2 ? "warning" : "");
          return `<span class="flow-step ${cls}">${s}</span>`;
        }).join(" &rarr; ");
      } else if (chainRow) {
        chainRow.style.display = "none";
      }

      if (evidenceEl && data.evidence_sources && data.evidence_sources.length > 0) {
        if (evidenceRow) evidenceRow.style.display = "flex";
        evidenceEl.innerHTML = data.evidence_sources.map(ev => `
          <a class="evidence-pill" href="javascript:void(0)" onclick="app.handleEvidenceClick('${ev.id}')">${ev.id}</a>
        `).join("");
      } else if (evidenceRow) {
        evidenceRow.style.display = "none";
      }

      if (thread) thread.scrollTop = thread.scrollHeight;
    } catch (err) {
      if (aiEl) aiEl.textContent = `Ошибка анализа: ${err.message}`;
    }
  },

  handleEvidenceClick(sourceId) {
    if (sourceId.startsWith("news:")) {
      this.openDetailSheet(this.currentNewsId);
    } else if (sourceId.startsWith("alfa:")) {
      this.switchTab("research");
    } else if (sourceId.startsWith("company:")) {
      this.toggleClientModal();
    } else {
      this.switchTab("payments");
    }
  },

  async loadDailyBriefing() {
    const thread = document.getElementById("chatgptThread");
    if (thread) thread.style.display = "flex";

    // Append user starter request bubble
    const hist = document.getElementById("chatgptHistoryContainer");
    if (hist) {
      const uMsg = document.createElement("div");
      uMsg.className = "chatgpt-msg user";
      uMsg.innerHTML = `<div class="chatgpt-user-bubble">Сформируй суточный дайджест рисков и возможностей (Daily Briefing)</div>`;
      hist.appendChild(uMsg);
    }

    const aiEl = document.getElementById("hubAiText");
    const factEl = document.getElementById("hubFactText");
    const alfaEl = document.getElementById("hubAlfaText");
    const flowEl = document.getElementById("hubChainFlow");
    const chainRow = document.getElementById("hubChainRow");
    const respMsg = document.getElementById("chatgptActiveResponseMsg");

    if (respMsg) respMsg.style.display = "flex";
    if (aiEl) aiEl.innerHTML = "<em>Загрузка суточного дайджеста рисков и возможностей...</em>";

    if (thread) thread.scrollTop = thread.scrollHeight;

    try {
      const res = await fetch(`/api/briefing?uid=${this.currentClientUid}&role=${encodeURIComponent(this.currentRole)}`);
      const data = await res.json();

      if (factEl) factEl.textContent = `Сводка за 24 часа (${data.date}): 3 риска, 2 возможности, 1 спорный кейс.`;
      if (alfaEl) alfaEl.textContent = `ЦМИ Альфа-Банка: ${data.risks[0].title}. Рекомендация: ${data.risks[0].action}`;
      
      let briefingHtml = `<strong>Суточный дайджест для роли ${this.currentRole}:</strong><br/>`;
      data.risks.forEach((r, i) => {
        briefingHtml += `• <strong>Риск ${i+1}:</strong> ${r.title} [${r.dimension}] — <em>${r.action}</em><br/>`;
      });
      data.opportunities.forEach((o, i) => {
        briefingHtml += `• <strong>Возможность ${i+1}:</strong> ${o.title} — <em>${o.benefit}</em><br/>`;
      });
      briefingHtml += `• <strong>Спорная тема:</strong> ${data.controversial.title} — <em>${data.controversial.solution}</em>`;

      if (aiEl) aiEl.innerHTML = briefingHtml;
      if (chainRow) chainRow.style.display = "flex";
      if (flowEl) flowEl.innerHTML = `<span class="flow-step warning">3 Риска P&L</span> &rarr; <span class="flow-step success">2 Окна возможностей</span> &rarr; <span class="flow-step">1 Решение ALCO</span>`;

      if (thread) thread.scrollTop = thread.scrollHeight;
    } catch (err) {
      if (aiEl) aiEl.textContent = `Ошибка дайджеста: ${err.message}`;
    }
  },

  async loadExecutiveDelta() {
    // Append user starter request bubble
    const hist = document.getElementById("chatgptHistoryContainer");
    if (hist) {
      const uMsg = document.createElement("div");
      uMsg.className = "chatgpt-msg user";
      uMsg.innerHTML = `<div class="chatgpt-user-bubble">Что изменилось с моего прошлого входа в систему? (Executive Delta)</div>`;
      hist.appendChild(uMsg);
    }

    const aiEl = document.getElementById("hubAiText");
    const factEl = document.getElementById("hubFactText");
    const alfaEl = document.getElementById("hubAlfaText");
    const flowEl = document.getElementById("hubChainFlow");
    const respMsg = document.getElementById("chatgptActiveResponseMsg");

    if (respMsg) respMsg.style.display = "flex";
    if (aiEl) aiEl.innerHTML = "<em>Сравнение с предыдущей версией портфеля...</em>";

    const thread = document.getElementById("chatgptThread");
    if (thread) {
      thread.style.display = "flex";
      thread.scrollTop = thread.scrollHeight;
    }

    try {
      const res = await fetch(`/api/delta?uid=${this.currentClientUid}`);
      const data = await res.json();

      if (factEl) factEl.textContent = `Последний вход: ${data.last_login}. Новых рыночных событий: ${data.new_events_count}.`;
      if (alfaEl) alfaEl.textContent = `Аналитика Альфа-Банка: зафиксировано усиление сигнала регулятора и рост концентрации риска поставщика.`;

      let deltaHtml = `<strong>Что изменилось с прошлого раза:</strong><br/>`;
      data.changes.forEach((c) => {
        deltaHtml += `• <strong>${c.event}:</strong> ${c.change} [${c.status}] &rarr; <em>${c.action}</em><br/>`;
      });

      if (aiEl) aiEl.innerHTML = deltaHtml;
      if (flowEl) flowEl.innerHTML = `<span class="flow-step">Вход вчера 18:30</span> &rarr; <span class="flow-step warning">+3 Сдвига рынка</span> &rarr; <span class="flow-step success">Лимиты обновлены</span>`;

      if (thread) thread.scrollTop = thread.scrollHeight;
    } catch (err) {
      if (aiEl) aiEl.textContent = `Ошибка дельты: ${err.message}`;
    }
  },

  async sendFeedback(feedbackType, targetId) {
    try {
      await fetch("/api/news/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback: feedbackType,
          target_id: targetId,
          uid: this.currentClientUid,
          role: this.currentRole,
          timestamp: new Date().toISOString()
        })
      });
      alert(feedbackType === "thumbs_up" ? "Спасибо! Ваша оценка принята. Модель адаптирует веса релевантности." : "Спасибо! Событие помечено как малозначимое для Вашего профиля.");
    } catch (e) {
      console.error(e);
    }
  },

  copyToAlco() {
    const aiEl = document.getElementById("hubAiText");
    if (!aiEl) return;
    const text = aiEl.innerText || aiEl.textContent;
    navigator.clipboard.writeText(`ВЫПИСКА ДЛЯ КОМИТЕТА ALCO (Альфа-Инсайт):\n${text}`);
    alert("Аналитический вывод скопирован в буфер обмена для заседания ALCO.");
  },


  async openDetailSheet(newsId) {
    this.currentNewsId = newsId;
    const backdrop = document.getElementById("detailSheetBackdrop");
    backdrop.classList.remove("hidden");

    // Clear previous
    document.getElementById("sheetNewsTitle").textContent = "Загрузка детального анализа (8 шагов AI)...";

    try {
      const res = await fetch(`/api/news/insight?uid=${this.currentClientUid}&news_id=${newsId}&role=${encodeURIComponent(this.currentRole)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const insight = data.insight;
      document.getElementById("sheetNewsTitle").textContent = insight.event_title || "Детальный анализ бизнес-события";
      
      const badge = document.getElementById("sheetRelevanceBadge");
      if (badge && insight.impact_chain) {
        badge.textContent = `${insight.impact_chain.impact_strength} • ${insight.impact_chain.time_horizon}`;
      }

      // 1. RAG GROUNDING MATRIX (ITEM 8)
      if (insight.fact_to_insight_matrix) {
        const m = insight.fact_to_insight_matrix;
        document.getElementById("sheetFactText").textContent = m.fact ? m.fact.title : "Первичный факт регулятора";
        document.getElementById("sheetResearchText").textContent = m.bank_research ? `${m.bank_research.title}: ${m.bank_research.key_quote}` : "Исследование ЦМИ Альфа-Банка";
        document.getElementById("sheetCompanyFeatures").textContent = (m.client_features || []).join(" • ");
        document.getElementById("sheetInsightConclusion").textContent = m.conclusion || "Защита маржинальности и управление свободным денежным потоком.";
      }

      // 2. IMPACT CHAIN (ITEM 7)
      const chainWrap = document.getElementById("sheetChainSteps");
      if (chainWrap && insight.impact_chain && insight.impact_chain.steps) {
        document.getElementById("sheetStrengthPill").textContent = `Сила: ${insight.impact_chain.impact_strength}`;
        document.getElementById("sheetHorizonPill").textContent = `Горизонт: ${insight.impact_chain.time_horizon}`;

        chainWrap.innerHTML = insight.impact_chain.steps.map((st, idx) => {
          const dir = st.direction === "UP" ? "↑" : (st.direction === "DOWN" ? "↓" : "↔");
          return `
            <div class="chain-step-chip">
              <span class="chip-step-num">Шаг ${idx + 1}</span>
              <div class="chip-step-title">${st.step_title}</div>
              <div class="chip-step-metric">
                <span>${st.metric_affected.toUpperCase()}</span>
                <strong style="color: ${st.direction === 'DOWN' ? '#F87171' : '#34D399'}">${dir} ${st.direction}</strong>
              </div>
            </div>
          `;
        }).join("");
      }

      // 3. CRITIC CHECK (ITEM 12)
      const noveltyBadge = document.getElementById("sheetNoveltyBadge");
      if (noveltyBadge) noveltyBadge.textContent = `Новизна: ${insight.novelty_score || 95}%`;

      // 4. 6 PILLARS
      const pillarsWrap = document.getElementById("sheetPillars");
      if (pillarsWrap) {
        const pList = [
          { num: 1, title: "Что произошло? (Фактология)", text: insight.what_happened },
          { num: 2, title: `Почему это важно для Вашей компании?`, text: insight.why_it_matters },
          { num: 3, title: "Какие последствия возможны? (Риски и возможности)", text: insight.potential_consequences },
          { num: 4, title: `Какие действия релевантны? (План для роли ${this.currentRole})`, text: insight.recommended_actions },
          { num: 5, title: "Экспертная позиция ЦМИ Альфа-Банка", text: insight.bank_expert_perspective },
          { num: 6, title: "На чем основан вывод? (Data Lineage & Трассировка)", text: `Признаки: ${(insight.data_lineage.client_features_utilized || []).join(", ")}. Модель: ${insight.data_lineage.ai_inference_method}` },
        ];

        pillarsWrap.innerHTML = pList.map((p) => `
          <div class="pillar-box">
            <div class="pillar-box-title">
              <span style="color: #EF3124; font-weight: 800;">${p.num}.</span>
              <span>${p.title}</span>
            </div>
            <p class="pillar-box-text">${this.formatMarkdown(p.text)}</p>
          </div>
        `).join("");
      }

      // 5. PRODUCTS
      const prodsWrap = document.getElementById("sheetProducts");
      if (prodsWrap && insight.suggested_bank_products) {
        prodsWrap.innerHTML = insight.suggested_bank_products.map((pr) => `
          <div class="prod-banner">
            <div>
              <div class="prod-banner-title">${pr.product_name}</div>
              <div class="prod-banner-desc">${pr.benefit}</div>
            </div>
            <button class="prod-banner-btn" onclick="alert('Заявка по продукту «${pr.product_name}» направлена персональному менеджеру крупного бизнеса.')">
              ${pr.action_text}
            </button>
          </div>
        `).join("");
      }

    } catch (err) {
      document.getElementById("sheetNewsTitle").textContent = `Ошибка анализа: ${err.message}`;
    }
  },

  closeDetailSheet() {
    const backdrop = document.getElementById("detailSheetBackdrop");
    backdrop.classList.add("hidden");
  },

  switchTab(tabId) {
    document.querySelectorAll(".tab-view").forEach((v) => v.classList.remove("active"));
    document.querySelectorAll(".dock-tab").forEach((b) => b.classList.remove("active"));

    const targetView = document.getElementById(tabId);
    if (targetView) targetView.classList.add("active");

    const targetBtn = document.querySelector(`.dock-tab[data-tab="${tabId}"]`);
    if (targetBtn) targetBtn.classList.add("active");
  },

  toggleGroup(groupId) {
    const group = document.getElementById(groupId);
    const arrow = document.getElementById(groupId + "Arrow");
    if (!group) return;
    if (group.style.display === "none") {
      group.style.display = "flex";
      if (arrow) arrow.textContent = "⌃";
    } else {
      group.style.display = "none";
      if (arrow) arrow.textContent = "⌄";
    }
  },

  scrollCarousel(direction) {
    const c = document.getElementById("storiesCarousel");
    if (c) c.scrollBy({ left: direction * 240, behavior: "smooth" });
  },

  openStory(storyKey) {
    if (storyKey === "rate") this.openDetailSheet("NEWS-2026-09-001");
    else if (storyKey === "turkey") this.openDetailSheet("NEWS-2026-09-002");
    else if (storyKey === "subsidy") this.openDetailSheet("NEWS-2026-09-003");
    else this.openDetailSheet("NEWS-2026-09-004");
  },

  openImpactChainDemo() {
    this.openDetailSheet("NEWS-2026-09-001");
  },

  showAgenticTraceModal() {
    this.openDetailSheet("NEWS-2026-09-001");
  },

  filterNewsBySearch(text) {
    const q = text.toLowerCase().trim();
    if (!q) {
      this.renderNewsFeed(this.currentFeed);
      return;
    }
    const filtered = this.currentFeed.filter((item) => {
      return item.news.title.toLowerCase().includes(q) || item.news.summary.toLowerCase().includes(q);
    });
    this.renderNewsFeed(filtered);
  },

  setFeedFilter(level, btn) {
    this.filterLevel = level;
    document.querySelectorAll(".feed-filter-chips .chip").forEach((c) => c.classList.remove("active"));
    if (btn) btn.classList.add("active");
    this.renderNewsFeed(this.currentFeed);
  },

  toggleClientModal() {
    const m = document.getElementById("clientModalBackdrop");
    m.classList.toggle("hidden");
  },

  async changeClientFromModal(uid) {
    this.currentClientUid = uid;
    await this.refreshCurrentClientView();
  },

  async changeRoleFromModal(role) {
    this.currentRole = role;
    await this.refreshCurrentClientView();
  },

  requestNewProduct() {
    alert("Заявка на подключение нового корпоративного продукта (Овернайт, IRS-своп, ВЭД-аккредитив) сформирована персональному менеджеру Альфа-Банка.");
  },

  async handleSendChat() {
    const input = document.getElementById("chatTextInput");
    const q = input.value.trim();
    if (!q) return;

    const thread = document.getElementById("chatThread");
    
    // User message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg user";
    userMsg.innerHTML = `<div class="msg-avatar">Я</div><div class="msg-bubble">${q}</div>`;
    thread.appendChild(userMsg);
    input.value = "";
    thread.scrollTop = thread.scrollHeight;

    // AI loading message
    const aiMsg = document.createElement("div");
    aiMsg.className = "chat-msg ai";
    aiMsg.innerHTML = `<div class="msg-avatar">А</div><div class="msg-bubble"><em>Формирование аналитического ответа на базе исследований ЦМИ Альфа-Банка...</em></div>`;
    thread.appendChild(aiMsg);
    thread.scrollTop = thread.scrollHeight;

    try {
      const res = await fetch("/api/assistant/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          uid: this.currentClientUid,
          news_id: this.currentNewsId,
          question: q,
          role: this.currentRole,
        }),
      });
      const data = await res.json();
      aiMsg.querySelector(".msg-bubble").innerHTML = this.formatMarkdown(data.answer);
      thread.scrollTop = thread.scrollHeight;
    } catch (err) {
      aiMsg.querySelector(".msg-bubble").textContent = `Ошибка ответа: ${err.message}`;
    }
  },

  async loadCounterpartyGraph() {
    try {
      const res = await fetch(`/api/client/${this.currentClientUid}`);
      const data = await res.json();
      const exposures = data.counterparty_exposures || [];
      const tbody = document.querySelector("#counterpartyTable tbody");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (exposures.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">Контрагенты не найдены.</td></tr>';
      } else {
        exposures.forEach((exp) => {
          const tr = document.createElement("tr");
          const riskColor = exp.risk_level === "HIGH" ? "color: #EF3124; font-weight:700;" : (exp.risk_level === "MEDIUM" ? "color: #F59E0B; font-weight:700;" : "color: #10B981;");
          tr.innerHTML = `
            <td><strong>${exp.counterparty_name}</strong></td>
            <td>${exp.relation_type}</td>
            <td>${(exp.payment_amount / 1e9).toFixed(2)} млрд ₽</td>
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
    if (!canvas) return;
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      canvas.innerHTML = '<div style="color: #8E93A0; font-size: 12px;">Нет связей для визуализации</div>';
      return;
    }

    const width = 480;
    const height = 280;
    const centerX = width / 2;
    const centerY = height / 2;

    const rootNode = graphData.nodes.find((n) => n.is_root) || graphData.nodes[0];
    const otherNodes = graphData.nodes.filter((n) => n.id !== rootNode.id);

    let svgHtml = `<svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" style="background: transparent;">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#606470"/>
        </marker>
      </defs>`;

    const radius = 105;
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
      const s = nodeCoords[e.from_id];
      const t = nodeCoords[e.to_id];
      if (s && t) {
        const color = e.is_critical ? "#EF3124" : "#4A4D59";
        svgHtml += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="${color}" stroke-width="2" marker-end="url(#arrow)"/>`;
      }
    });

    // Draw other nodes
    otherNodes.forEach((node) => {
      const c = nodeCoords[node.id];
      svgHtml += `
        <circle cx="${c.x}" cy="${c.y}" r="22" fill="#222328" stroke="#3A3C45" stroke-width="2"/>
        <text x="${c.x}" y="${c.y - 3}" font-size="9" font-weight="700" text-anchor="middle" fill="#FFFFFF">${node.id}</text>
        <text x="${c.x}" y="${c.y + 9}" font-size="7.5" text-anchor="middle" fill="#8E93A0">${node.revenue_bln} млрд ₽</text>
      `;
    });

    // Central root
    svgHtml += `
      <circle cx="${centerX}" cy="${centerY}" r="28" fill="#EF3124" stroke="#B91C1C" stroke-width="2"/>
      <text x="${centerX}" y="${centerY - 3}" font-size="10" font-weight="800" text-anchor="middle" fill="#FFFFFF">${rootNode.id}</text>
      <text x="${centerX}" y="${centerY + 10}" font-size="8" text-anchor="middle" fill="#FFF">${rootNode.revenue_bln} млрд ₽</text>
    `;

    svgHtml += "</svg>";
    canvas.innerHTML = svgHtml;
  },

  async loadResearch() {
    const grid = document.getElementById("researchGrid");
    if (!grid) return;
    try {
      const res = await fetch("/api/research");
      const reports = await res.json();
      grid.innerHTML = "";

      reports.forEach((r) => {
        const tile = document.createElement("div");
        tile.className = "research-tile";
        tile.innerHTML = `
          <div style="font-size: 10px; font-weight: 700; color: #EF3124; text-transform: uppercase;">${r.author} • ${r.date}</div>
          <h4>${r.title}</h4>
          <p>${r.summary}</p>
        `;
        grid.appendChild(tile);
      });
    } catch (err) {
      grid.innerHTML = `<div class="loading-spinner-box">Ошибка загрузки аналитики: ${err.message}</div>`;
    }
  },

  formatMarkdown(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\[(.*?)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #EF3124; text-decoration: underline; font-weight: 600;">$1 &nearr;</a>')
      .replace(/\n\n/g, "<br><br>")
      .replace(/\n/g, "<br/>");
  },
};

window.addEventListener("DOMContentLoaded", () => {
  app.init();
});
