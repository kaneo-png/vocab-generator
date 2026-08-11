// チャットUI制御（AI駆動ヒアリング対応版）
let sessionKey = localStorage.getItem("chat_session_key") || null;
let isGenerating = false;
let isCompleted = false;

const messagesEl = document.getElementById("chat-messages");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");
const statusEl = document.getElementById("chat-status");

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = text;
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setInputEnabled(enabled) {
    inputEl.disabled = !enabled;
    sendBtn.disabled = !enabled;
    if (enabled) {
        inputEl.focus();
    }
}

function setStatus(text) {
    statusEl.textContent = text || "";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// 収集データを修正するためのUIを表示する
function showEditSummary(collectedData) {
    const container = document.getElementById("edit-summary");
    if (!container) return;

    const labels = {
        goal: "🎯 学習目標",
        level: "📊 レベル",
        weak_points: "📝 苦手分野",
        count: "🔢 単語数",
        other_requests: "📌 その他要望",
    };

    const fields = ["goal", "level", "weak_points", "count", "other_requests"]
        .filter(k => collectedData[k])
        .map(k => `
            <div class="edit-field">
                <label>${labels[k] || k}</label>
                <input type="text" id="edit-${k}" value="${escapeHtml(String(collectedData[k]))}">
            </div>
        `).join("");

    container.innerHTML = `
        <h3>📝 入力内容の確認・修正</h3>
        <div class="edit-fields">${fields}</div>
        <button id="apply-edits" class="btn btn-outline btn-sm">修正を反映</button>
    `;
    container.style.display = "block";

    document.getElementById("apply-edits").addEventListener("click", async () => {
        const data = {};
        ["goal", "level", "weak_points", "count", "other_requests"].forEach(k => {
            const el = document.getElementById(`edit-${k}`);
            if (el) data[k] = el.value.trim();
        });
        await updateCollectedData(data);
    });
}

// 収集データをサーバーに反映（PUT）
async function updateCollectedData(data) {
    if (!sessionKey) return;
    try {
        const res = await fetch(`/api/chat/session/${sessionKey}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const result = await res.json();
        if (res.ok) {
            addMessage("✅ 修正を反映しました。", "bot");
            if (result.status === "completed") {
                showGenerateButton();
            }
        }
    } catch (e) {
        addMessage("修正の反映に失敗しました。", "bot");
    }
}

// 単語帳生成ボタンを表示する
function showGenerateButton() {
    if (isCompleted) return;
    isCompleted = true;
    const div = document.createElement("div");
    div.className = "wordlist-result";
    div.innerHTML = `
        <h2>🎉 入力完了！</h2>
        <p>この内容で単語帳を生成しますか？</p>
        <div class="result-actions">
            <button id="btn-generate" class="btn btn-primary">単語帳を生成</button>
        </div>
    `;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    document.getElementById("btn-generate").addEventListener("click", () => {
        generateWordlist();
    });
}

// セッション開始（初回アクセス時）
async function startSession() {
    setStatus("セッションを開始しています...");
    try {
        const res = await fetch("/api/chat/session", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            sessionKey = data.session_key;
            localStorage.setItem("chat_session_key", sessionKey);
            addMessage(escapeHtml(data.message || "学習目標を教えてください。"), "bot");
        } else {
            addMessage(`エラー: ${escapeHtml(data.error || "セッション開始に失敗")}`, "bot");
        }
    } catch (e) {
        addMessage("サーバーに接続できませんでした。", "bot");
    }
    setStatus("");
    setInputEnabled(true);
}

// メッセージ送信
async function sendUserMessage(text) {
    if (!text.trim() || isGenerating || !sessionKey) return;

    addMessage(escapeHtml(text), "user");
    inputEl.value = "";
    setInputEnabled(false);
    setStatus("AIが回答を考えています...");

    try {
        const res = await fetch("/api/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_key: sessionKey, message: text }),
        });
        const data = await res.json();

        if (!res.ok) {
            addMessage(`エラー: ${escapeHtml(data.error || "不明なエラー")}`, "bot");
            setInputEnabled(true);
            setStatus("");
            return;
        }

        addMessage(escapeHtml(data.message || ""), "bot");

        // 収集データの編集サマリーを更新
        showEditSummary(data.collected_data || {});

        // 完了時は生成ボタン表示
        if (data.status === "completed" || data.summary) {
            if (data.summary) {
                addMessage(`📋 学習プランまとめ:<br>${escapeHtml(data.summary)}`, "bot");
            }
            showGenerateButton();
        }
    } catch (e) {
        addMessage("通信エラーが発生しました。もう一度お試しください。", "bot");
    }

    setStatus("");
    setInputEnabled(true);
}

// 単語帳生成
async function generateWordlist() {
    if (!sessionKey) return;
    isGenerating = true;
    setInputEnabled(false);
    setStatus("AIが単語リストを生成中...（数秒かかります）");

    try {
        // セッションから収集データを取得
        const sres = await fetch(`/api/chat/session/${sessionKey}`);
        const sdata = await sres.json();
        const cd = sdata.collected_data || {};

        const response = await fetch("/api/chat/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                goal: cd.goal || "",
                level: cd.level || "",
                weak_points: cd.weak_points || "",
                count: parseInt(cd.count, 10) || 20,
                chat_history: [],
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            if (data.limit_reached) {
                addMessage(
                    "⚠️ 今月の生成回数上限に達しました。<br>" +
                    `<a href="/billing/plans">プランをアップグレード</a>すると続けて利用できます。`,
                    "bot"
                );
            } else {
                addMessage(`エラー: ${escapeHtml(data.error || "不明なエラー")}`, "bot");
            }
            setStatus("");
            setInputEnabled(true);
            isGenerating = false;
            return;
        }

        // 生成結果を表示
        addMessage(`✅ 単語帳「${escapeHtml(data.title)}」が完成しました！（残り${data.remaining}回）`, "bot");

        const resultDiv = document.createElement("div");
        resultDiv.className = "wordlist-result";
        resultDiv.innerHTML = `
            <h2>${escapeHtml(data.title)}</h2>
            ${data.words.map(w => `
                <div class="word-item">
                    <div class="word">${escapeHtml(w.word)}</div>
                    <div class="meaning">${escapeHtml(w.meaning)}</div>
                    ${w.example ? `<div class="example">${escapeHtml(w.example)}</div>` : ""}
                </div>
            `).join("")}
            <div class="result-actions">
                <a href="/api/wordlists/${data.wordlist_id}/csv" class="btn btn-primary">CSVダウンロード</a>
                <a href="/dashboard" class="btn btn-outline">ダッシュボードへ</a>
            </div>
        `;
        messagesEl.appendChild(resultDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        setStatus("");
        inputEl.placeholder = "単語帳が作成されました。";
    } catch (err) {
        addMessage("通信エラーが発生しました。もう一度お試しください。", "bot");
        setStatus("");
        setInputEnabled(true);
        isGenerating = false;
    }
}

// イベントリスナー
sendBtn.addEventListener("click", () => {
    sendUserMessage(inputEl.value);
    inputEl.value = "";
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendUserMessage(inputEl.value);
        inputEl.value = "";
    }
});

// 初期化
setInputEnabled(false);
startSession();
