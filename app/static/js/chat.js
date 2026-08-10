// チャットUI制御
// ステップ: 1=目標, 2=レベル, 3=苦手分野, 4=単語数, 5=生成確認
let currentStep = 1;
let chatData = {
    goal: "",
    level: "",
    weak_points: "",
    count: 20,
    chat_history: [],
};
let isGenerating = false;

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

function handleUserInput(text) {
    if (!text.trim() || isGenerating) return;

    addMessage(escapeHtml(text), "user");
    chatData.chat_history.push({ role: "user", content: text });

    switch (currentStep) {
        case 1:
            chatData.goal = text.trim();
            currentStep = 2;
            addMessage("ありがとうございます！次に、現在の英語レベルを教えてください。<br>（例: 初級 / 中級 / 上級 / TOEIC 600点程度）", "bot");
            break;
        case 2:
            chatData.level = text.trim();
            currentStep = 3;
            addMessage("次に、苦手な分野や強化したい分野はありますか？<br>（例: ビジネス英単語 / 日常会話 / 試験対策 / 特になし）", "bot");
            break;
        case 3:
            chatData.weak_points = text.trim() || "特になし";
            currentStep = 4;
            addMessage("何語くらいの単語帳を作成しますか？<br>（例: 20 / 30 / 50）", "bot");
            break;
        case 4:
            const count = parseInt(text, 10);
            chatData.count = isNaN(count) ? 20 : Math.min(Math.max(count, 5), 50);
            currentStep = 5;
            addMessage(
                `以下の内容で単語帳を生成します。<br>` +
                `🎯 目標: ${escapeHtml(chatData.goal)}<br>` +
                `📊 レベル: ${escapeHtml(chatData.level)}<br>` +
                `📝 苦手分野: ${escapeHtml(chatData.weak_points)}<br>` +
                `🔢 単語数: ${chatData.count}語<br><br>` +
                `「生成」と入力してください。`,
                "bot"
            );
            break;
        case 5:
            if (text.trim() === "生成") {
                generateWordlist();
            } else {
                addMessage("「生成」と入力すると単語帳を作成します。", "bot");
            }
            break;
    }
}

async function generateWordlist() {
    isGenerating = true;
    setInputEnabled(false);
    setStatus("AIが単語リストを生成中...（数秒かかります）");

    try {
        const response = await fetch("/api/chat/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(chatData),
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
        setInputEnabled(false);
        inputEl.placeholder = "単語帳が作成されました。";
    } catch (err) {
        addMessage("通信エラーが発生しました。もう一度お試しください。", "bot");
        setStatus("");
        setInputEnabled(true);
        isGenerating = false;
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// イベントリスナー
sendBtn.addEventListener("click", () => {
    handleUserInput(inputEl.value);
    inputEl.value = "";
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleUserInput(inputEl.value);
        inputEl.value = "";
    }
});

// 初期化: 入力可能にする
setInputEnabled(true);