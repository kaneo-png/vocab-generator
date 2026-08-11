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
            ${data.words.map((w, idx) => `
                <div class="word-item">
                    <div class="word">${escapeHtml(w.word)}
                        ${w.difficulty ? `<span class="badge">${escapeHtml(w.difficulty)}</span>` : ""}
                        ${w.category ? `<span class="badge badge-cat">${escapeHtml(w.category)}</span>` : ""}
                    </div>
                    <div class="meaning">${escapeHtml(w.meaning)}</div>
                    ${w.reason ? `<div class="reason">💡 ${escapeHtml(w.reason)}</div>` : ""}
                    ${w.example ? `<div class="example">${escapeHtml(w.example)}</div>` : ""}
                    <div class="word-actions">
                        <button class="btn btn-outline btn-sm" onclick="editWord(${data.wordlist_id}, ${idx})">編集</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteWord(${data.wordlist_id}, ${idx})">削除</button>
                    </div>
                </div>
            `).join("")}
            <div class="result-actions">
                <button class="btn btn-outline" onclick="addWord(${data.wordlist_id})">＋ 単語を追加</button>
                <a href="/api/wordlists/${data.wordlist_id}/csv" class="btn btn-primary">CSVダウンロード</a>
                <a href="/dashboard" class="btn btn-outline">ダッシュボードへ</a>
            </div>
        `;
        messagesEl.appendChild(resultDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        window._lastWords = data.words;

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


// ===== 単語の編集・削除・追加 =====
let _wordlistId = null;

function editWord(listId, idx) {
    const w = window._lastWords[idx];
    _wordlistId = listId;
    const container = document.getElementById("edit-summary");
    container.innerHTML = `
        <h3>✏️ 単語を編集: ${escapeHtml(w.word)}</h3>
        <div class="edit-fields">
            <div class="edit-field"><label>単語</label><input id="ew-word" value="${escapeHtml(w.word)}"></div>
            <div class="edit-field"><label>意味</label><input id="ew-meaning" value="${escapeHtml(w.meaning)}"></div>
            <div class="edit-field"><label>例文</label><input id="ew-example" value="${escapeHtml(w.example || "")}"></div>
            <div class="edit-field"><label>例文の訳</label><input id="ew-example_ja" value="${escapeHtml(w.example_ja || "")}"></div>
            <div class="edit-field"><label>選定理由</label><input id="ew-reason" value="${escapeHtml(w.reason || "")}"></div>
            <div class="edit-field"><label>難易度</label><input id="ew-difficulty" value="${escapeHtml(w.difficulty || "")}"></div>
            <div class="edit-field"><label>カテゴリ</label><input id="ew-category" value="${escapeHtml(w.category || "")}"></div>
        </div>
        <button id="save-word" class="btn btn-primary btn-sm">保存</button>
        <button id="cancel-edit" class="btn btn-outline btn-sm">キャンセル</button>
    `;
    container.style.display = "block";

    document.getElementById("save-word").addEventListener("click", async () => {
        const data = {};
        ["word", "meaning", "example", "example_ja", "reason", "difficulty", "category"].forEach(k => {
            const el = document.getElementById(`ew-${k}`);
            if (el) data[k] = el.value.trim();
        });
        const res = await fetch(`/api/wordlists/${listId}/words/${w.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (res.ok) {
            container.style.display = "none";
            addMessage(`✅ 「${escapeHtml(data.word)}」を更新しました。`, "bot");
        } else {
            addMessage("更新に失敗しました。", "bot");
        }
    });
    document.getElementById("cancel-edit").addEventListener("click", () => {
        container.style.display = "none";
    });
}

function deleteWord(listId, idx) {
    const w = window._lastWords[idx];
    if (!confirm(`「${w.word}」を削除しますか？`)) return;
    fetch(`/api/wordlists/${listId}/words/${w.id}`, { method: "DELETE" })
        .then(res => {
            if (res.ok) {
                addMessage(`🗑️ 「${escapeHtml(w.word)}」を削除しました。`, "bot");
            } else {
                addMessage("削除に失敗しました。", "bot");
            }
        });
}

function addWord(listId) {
    _wordlistId = listId;
    const container = document.getElementById("edit-summary");
    container.innerHTML = `
        <h3>＋ 単語を追加</h3>
        <div class="edit-fields">
            <div class="edit-field"><label>単語（必須）</label><input id="aw-word"></div>
            <div class="edit-field"><label>意味</label><input id="aw-meaning"></div>
            <div class="edit-field"><label>例文</label><input id="aw-example"></div>
            <div class="edit-field"><label>例文の訳</label><input id="aw-example_ja"></div>
            <div class="edit-field"><label>選定理由</label><input id="aw-reason"></div>
            <div class="edit-field"><label>難易度</label><input id="aw-difficulty"></div>
            <div class="edit-field"><label>カテゴリ</label><input id="aw-category"></div>
        </div>
        <button id="save-new-word" class="btn btn-primary btn-sm">追加</button>
        <button id="cancel-add" class="btn btn-outline btn-sm">キャンセル</button>
    `;
    container.style.display = "block";

    document.getElementById("save-new-word").addEventListener("click", async () => {
        const data = {};
        ["word", "meaning", "example", "example_ja", "reason", "difficulty", "category"].forEach(k => {
            const el = document.getElementById(`aw-${k}`);
            if (el) data[k] = el.value.trim();
        });
        if (!data.word) {
            addMessage("単語を入力してください。", "bot");
            return;
        }
        const res = await fetch(`/api/wordlists/${listId}/words`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (res.ok) {
            container.style.display = "none";
            addMessage(`✅ 「${escapeHtml(data.word)}」を追加しました。`, "bot");
        } else {
            const err = await res.json();
            addMessage(`エラー: ${escapeHtml(err.error || "追加に失敗")}`, "bot");
        }
    });
    document.getElementById("cancel-add").addEventListener("click", () => {
        container.style.display = "none";
    });
}
