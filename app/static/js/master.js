// 試験対策単語帳ジェネレーターのフロントエンド制御
const statusEl = document.getElementById("master-status");
const resultEl = document.getElementById("master-result");

function setStatus(text) {
    statusEl.textContent = text || "";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// フォルダ追加
async function addFolder() {
    const nameInput = document.getElementById("new-folder-name");
    const name = nameInput.value.trim();
    if (!name) return;
    const res = await fetch("/api/master/folders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
    });
    if (res.ok) {
        const data = await res.json();
        const select = document.getElementById("folder-select");
        const opt = document.createElement("option");
        opt.value = data.id;
        opt.textContent = data.name;
        select.appendChild(opt);
        select.value = data.id;
        nameInput.value = "";
        setStatus(`✅ フォルダ「${data.name}」を作成しました`);
    }
}

// 単語帳生成
async function generateWordbook() {
    const examId = document.getElementById("exam-select").value;
    const folderId = document.getElementById("folder-select").value;
    const count = parseInt(document.getElementById("count-input").value, 10) || 50;
    const weakPoints = document.getElementById("weak-input").value.trim();

    if (!examId) {
        setStatus("試験を選択してください。");
        return;
    }

    setStatus("AIが単語を選定中...（数秒かかります）");
    document.getElementById("btn-generate").disabled = true;

    try {
        const res = await fetch("/api/master/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                exam_id: parseInt(examId, 10),
                folder_id: folderId ? parseInt(folderId, 10) : null,
                count,
                weak_points: weakPoints,
            }),
        });
        const data = await res.json();

        if (!res.ok) {
            setStatus(`エラー: ${data.error || "不明なエラー"}`);
            return;
        }

        setStatus(`✅ 単語帳「${data.title}」を生成しました（${data.words.length}語）`);
        resultEl.innerHTML = `
            <div class="wordlist-result">
                <h2>${escapeHtml(data.title)}</h2>
                ${data.words.map(w => `
                    <div class="word-item">
                        <div class="word">${escapeHtml(w.lemma)}</div>
                        <div class="meaning">${escapeHtml(w.meaning_ja)}</div>
                        <div class="reason">💡 ${escapeHtml(w.reason || "")}</div>
                    </div>
                `).join("")}
                <div class="result-actions">
                    <a href="/api/master/wordbooks/${data.wordbook_id}/csv" class="btn btn-primary">CSVダウンロード</a>
                </div>
            </div>
        `;
    } catch (e) {
        setStatus("通信エラーが発生しました。");
    } finally {
        document.getElementById("btn-generate").disabled = false;
    }
}

// イベントリスナー
document.getElementById("btn-add-folder").addEventListener("click", addFolder);
document.getElementById("btn-generate").addEventListener("click", generateWordbook);
