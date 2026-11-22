> 注（2026-11-22）: このレビューでいう `article.md` は初版の早期ドラフトです（コミット `1da2204` 時点の `article.md`、git 履歴を参照）。現在の `article.md` は open-weight 版の正本で、別物です。

# Review: "The Frugal Chatbot"（Claude 版ドラフト、2026-11-19）

対象は会話に貼り付けられた Claude 版ドラフトです。
`~/frugal-chatbot/article.md` は別バージョンです（Step 1〜7 構成、"I start with the most expensive model…" で始まる版）。そのため本レビューは article.md の行番号ではなく、ドラフトの節名で指しています。article.md には手を入れていません。

検証の状態は次の 3 段階で表記します。
- **[確認済]**: 一次情報（公式ドキュメント、または Anthropic の公式価格表）と照合したもの
- **[要確認]**: 照合できていないもの
- **[計算]**: 手元で再計算したもの

---

## 0. 総評

骨格はよくできています。「最高級モデルから始め、段ごとに何を失うかを問う」という構成と、"minimum viable floor" という判定基準の導入がその中心です。

一方で、致命傷が 3 つあります（キャッシュ計算を含めると 4 つ）。
- **天井計算がトークン代を見ていない**
- **Lever 2 の算数ミス**
- **Stage 1 のコードがそのままでは動かない可能性が高い**

これに Lever 1（Nova のキャッシュ）の前提不成立を加えた 4 件を、1 章で【重大】としています。いずれも記事の主題である frugal と正確さに直撃します。AWS の読者はここを真っ先に突くはずです。

物語面の弱点は 2 つです。
- 各段の「floor は保たれる」が一度も検証されず断定されている
- Stage 3〜4 で数字がほぼ動かず、中だるみする

---

## 1. 技術的な正確さ

### 1-1. 【重大】"Put a ceiling on the worst case" はトークン代の上限になっていない
- ドラフトが示す $15/月は、Lambda compute 代だけの上限です。トークン代には触れていません。
- [計算] 同時実行 2 で 1 呼び出し 0.8 秒（ドラフト自身の前提）とすると、`2 × 2,592,000 s / 0.8 s ≈ 648 万回/月` 呼べます。
  - Nova Micro（$0.000091/回）でおよそ **$590/月**
  - Opus 5.5（$0.012/回）でおよそ **$77,760/月**
- 応答を 10 秒と現実的に置いても、Opus で 51.8 万回、**およそ $6,200/月**です。
- **AWS Budgets はアラートであって停止ではありません。** 請求データの反映には数時間〜1 日程度の遅延もあります。
- Function URL の保護策（CloudFront＋秘密ヘッダー、IAM、共有シークレット）は、**匿名の公開チャットボットには効きません**。ページを開いた人は誰でも正規クライアントとして叩けます。
- 必要な対策は次のとおりです。いずれも記事内で値段とトレードオフを明示すべきです。
  - レート制限（WAF は有料なので frugal と緊張関係にある）
  - 1 メッセージの長さ上限
  - 1 セッションあたりのターン上限
  - 日次トークン予算を DynamoDB でカウントして超えたら 503 を返す仕組み
- 冒頭の「3 時に wiki を丸ごと貼る」悪夢に対して、ハンドラは**メッセージの文字数を一切制限していません**。`[-6:]` が制限するのは件数で、サイズではありません。冒頭で提示した問題を本文が解いていない、という構成上の穴でもあります。

### 1-2. 【重大】Lever 2 の算数ミス
- 本文は "multiply its input tokens fivefold … the difference between $1.56 and nearly $8" と書いています。
- [計算] 入力だけを 5 倍にすると、`0.005 × $0.06 + 0.0004 × $0.24 = $0.000396/回`、つまり **$3.96/月** です。$7.8 になるのは出力も含めて全体を 5 倍にした場合で、前提と合いません。

### 1-3. 【重大】Lever 1 の Nova Lite キャッシュ計算は前提が成立しない
- [検索結果ベース・ほぼ確実] Bedrock のプロンプトキャッシュでは、Nova Micro/Lite/Pro のキャッシュチェックポイントに**最小 1K トークン**が必要です（[AWS Bedrock prompt caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)）。検索結果の要約で確認したもので、ページ本文は直接読んでいません。なお article.md 側の版もこの 1K 制約を明記しています。
- 600 トークンのプレフィックスは**キャッシュされません**。したがって「$1.29 instead of $1.56」は成立しません。チェックポイントは黙ってスキップされるという報告もあります（Caylent、[要確認]）。
- Claude 5.5 系の最小は 512 トークンなので、Haiku の $2.46 は前提上は成立しえます。ただし Anthropic 側のドキュメント自身が「Bedrock の最小値は AWS ドキュメントを見よ」としています。Bedrock 上の Claude の最小値は [要確認] です。
- **キャッシュ書き込みのプレミアム（Claude は 5 分 TTL で 1.25 倍）が計算に入っていません。**
- **ヒット率 100% を暗黙に仮定しています。** 10,000 chats/月は平均間隔約 4.3 分で、5 分 TTL とほぼ同じです。夜間はほぼ全部ミスになります。「平均間隔が TTL とほぼ同じ」こと自体が良い教材になるので、正直に書いた方が記事として強くなります。
- 600 トークンで「FAQ コンテキスト」が入るのは非現実的です。現実の FAQ ボットは system＋FAQ だけで数千トークンになります。入力を 1,000 トークンとした前提が全体を過小評価しており、キャッシュの価値も過小に見せています（2-3 も参照）。

### 1-4. 【重大】Stage 1 のコードはそのままでは動かない可能性が高い
- 以下の Claude 関連の事実（価格、512 トークン最小、思考トークンの課金、temperature の 400、Haiku のトークナイザ）は、Claude Code 同梱の claude-api スキルの参照資料（2026-11-03 キャッシュ、first-party API 前提）に拠ります。Bedrock Converse でも同じ挙動かはすべて [要確認] です。
- **`temperature: 0.7`**: 上記の参照資料では、Opus 5.5 / Sonnet 5.5 / Haiku 5.5 はデフォルト以外のサンプリングパラメータを 400 で拒否します。Bedrock の Converse 経由でも同様かは [要確認] ですが、少なくとも消すべきです。FAQ 用途なら温度を上げる理由もありません。
- **`[-6:]` のスライス**: クライアントは user で終わる奇数長の履歴を送ってきます。そのため 4 ターン目以降、6 件スライスの先頭が assistant になります。Converse は先頭が user であることを要求するので、ValidationException になるはずです（挙動は [要確認]）。`[-7:]` にするか、先頭の assistant を落とす処理が要ります。
- **思考トークン**（Bedrock でも既定でオンかは [要確認]）: Opus 5.5 は思考を無効化できず（effort が唯一の制御で、デフォルトは medium）、Sonnet 5.5 / Haiku 5.5 も適応思考がデフォルトでオンです。思考トークンは出力として課金されるので、次の 2 つが崩れます。
  - 「出力 400 トークン」という前提: 特に Opus で過小評価になる
  - `maxTokens: 512`: 思考が予算を食うと回答が途中で切れうる。effort を `low` に明示するのが筋で、そうすれば Lever として 1 つ増やせる
- **クライアントが履歴を丸ごと送る設計**: assistant 発話を偽造できるので、プロンプトインジェクションの温床になります。最低でも一言触れるべきです。
- **モデル ID**: 価格は global endpoint の料金で計算していますが、コードは素のモデル ID `anthropic.claude-opus-5-5` を使っています。global の料金を得るには `global.` 系の inference profile ID を指定するはずです（[要確認]）。価格の前提とコードが一致していません。

### 1-5. 「Bedrock で最も高価・最も高性能なモデル」は誤りの可能性
- [確認済：Anthropic 側] Claude Fable 5.2（$8/$40）は Opus 5.5 より上位かつ高価で、Bedrock でも「提供されている場所では」利用できる旨の記述があります。
- そのため、サブタイトルの "the most expensive model on Amazon Bedrock" と Stage 1 の "the most capable model on Bedrock" はおそらく誤りです。
- 次のどちらかで対処できます。
  - 表現を "the flagship of the Opus line" / "a flagship" に弱める
  - 「Fable 5.2 という更に上位・高価なモデルもあるが、チャットボットの出発点としては Opus を選んだ」と一言断る

### 1-6. ルーティングの $1.33 は甘い
- [計算] 0.8 × $0.91 ＋ 0.2 × $3 = $1.33 という計算は、**振り分けの判定がタダ**であることが前提です。
- 本文の「small model's answer smells uncertain なら上げる」方式なら、エスカレーション分は Micro と Haiku の両方を払います。0.2 × $0.91 を足して **$1.51**、さらに判定コストが乗ります。

### 1-7. Lambda 実行時間 800ms は非現実的
- 出力 400 トークンの非ストリーミング応答は、Opus なら数秒〜十数秒、Nova Micro でも 1〜数秒かかります。
- 無料枠に収まるという結論は変わりません。[計算] 10 秒でも 25,000 GB 秒で、無料枠の 6% です。
- ただし Lambda のデフォルトタイムアウトは **3 秒**です。これを延ばす手順が書かれていないので、how-to として読者が確実に詰まります。

### 1-8. DynamoDB の扱い
- 「履歴をリロード後も残すなら DynamoDB」と言いながら、コードには一度も出てきません（履歴はクライアントが送っている）。使うならコードを示す、使わないなら Stage 1 と Stage 4 から削る、のどちらかにすべきです。
- 常時無料の 25 RCU/WCU は**プロビジョンドモード**の話です。コンソールのデフォルトになりがちなオンデマンドでは適用されないはずで（[要確認]）、「Provisioned で作れ」と一言書く必要があります。

### 1-9. Function URL の保護
- 「CloudFront＋秘密ヘッダー」より、**CloudFront OAC による Lambda Function URL の保護**の方が現在の推奨パターンです（[要確認]：POST では `x-amz-content-sha256` ヘッダーが必要になる点にも注意）。
- ただし 1-1 のとおり、OAC にしても匿名の濫用は防げません。

### 1-10. WebLLM / WebGPU の記述
- **Safari のバージョンはおそらく誤り**: WebGPU がデフォルトで有効になったのは **Safari 26**（2025 年 9 月、iOS 26 / macOS Tahoe）で、18 ではありません（[Safari 26 coverage](https://appdevelopermagazine.com/webgpu-in-ios-26/), [WWDC25 WebKit notes](https://discuss.privacyguides.net/t/news-from-wwdc25-webkit-in-safari-26-beta/28226)）。どちらも二次情報なので、Apple のリリースノートでも確認してください。
- Firefox 141（Windows）と Chrome / Edge 113 は概ね正しいと思われます（[要確認]）。
- **Stage 5 のスニペットに FAQ コンテキストが入っていません。** これは floor を満たす同じチャットボットではありません。system に FAQ を入れたうえで、WebLLM 側のコンテキスト長（モデル設定次第で 4K 程度）に収まるかを示す必要があります。
- 「1B モデルは知らないと認めて断れる」は、小型モデルが最も苦手とする能力です。"holds — barely" と根拠なく言い切るのは危険です。
- **Hugging Face への依存**: 7TB の配信を第三者の無償帯域に肩代わりさせることになります。これはドラフト自身が冒頭で定義した "cheap"（手を抜いて誰も気づかないことを願う）に近く、記事のテーマと逆を向いています。加えて次の点にも一言触れるべきです。
  - 可用性・レート制限の保証がない
  - 訪問者の IP が HF に渡る（プライバシー）
  - Llama のライセンスと利用規約
- 「バッテリーが計算予算になる」も同じ構図です。honest limits に入れてあるのは良い点です。
- モデルサイズの数値（Llama 3.2 1B ≈ 700MB / 880MB VRAM、Qwen3 0.6B ≈ 335MB）は [要確認] のままです。WebLLM の prebuilt model list と照合してください。

---

## 2. How-to としての具体性

読者が再現しようとすると、次の箇所で詰まります。
1. IAM ロール（`bedrock:InvokeModel` と inference profile ARN）、Bedrock のモデルアクセス有効化
2. Lambda タイムアウトの延長、メモリ設定
3. CORS（Function URL の CORS 設定）
4. フロントエンド（チャット UI が `messages` を送る形式）が一切ない。Stage 1〜4 の静的ページがどこから来るのか不明
5. Stage 3 の cachePoint で `usage` の `cacheReadInputTokens` を見てヒットを確認する手順がない。キャッシュは黙って効かないのが最大の罠なので必須
6. ルーティングの「uncertain の判定」をどう実装するかのコードやプロンプトがない
7. Stage 5 のハイブリッド（WebGPU が使えなければ Bedrock に落とす）を 1 行で済ませている。`navigator.gpu` の判定コード 5 行で十分なので載せるべき
8. 履歴要約（Lever 2）のコードがない

提案は 2 つです。
- Stage 1 に IaC（SAM か CDK の 30 行程度）を 1 つ添えて、IAM、タイムアウト、Function URL、予約同時実行をまとめて片付ける。予約同時実行 2 は Stage 4 の天井と同じ設定なので、ここで出しておくと Stage 4 の説得力も増す
- 各段に `modelId` と価格の対応表を置く

---

## 3. 文章の流れ・冗長さ・物語として

### 3-1. 【重大】floor が一度も検証されない
- 記事の背骨である「各段で floor は保たれるか？」が、全段で書き手の印象による断定になっています。
- "desk calculations, not measurements" は価格については誠実です。しかし品質の判定まで机上なのは、読者から見ると「結論ありき」に映ります。
- **最小限の評価を入れると記事の格が一段上がります。**
  - 内容: FAQ 内の質問 20 問、範囲外の質問 5 問、言い換え・多段の質問 5 問の計 30 問程度
  - 対象: 各段のモデル
  - 採点: 正答率と、範囲外で断れた率
  - 費用: [計算] 思考トークンを考慮しても全段で数ドル以内
- これができないなら、「品質は筆者の見立て」と明記したうえで、各段の判定をトーンダウンすべきです。

### 3-2. 中だるみ
- Stage 2 で「最初の 2 段で $117 を削った。以降は polishing」と自分で宣言しています。
- その後 Stage 3〜4 は数字が $0.91 前後からほぼ動かず、Stage 5 で $0.91 → $0 になります。ドラマの最終盤が**月 1 ドル未満の節約**であり、しかもその代償に品質を大きく落としています。
- 改善案:
  - **Lever は Opus 段で効かせて見せる**。[計算] Opus＋キャッシュで約 $97、effort low＋出力キャップでさらに下がる。cents 単位の Nova で見せるより、ドル単位の上の段で見せる方が面白い
  - **規模の感度表を入れる**（10k / 100k / 1M chats）。1M chats なら Micro で $91、Haiku で $300 になり、ブラウザ推論が「意味を持つ」規模が見える。オチの説得力は、規模を変えたときに初めて生まれる
  - Stage 5 の正当化は、ドラフトの結論が既に半分そう言っているとおり、**コストよりもプライバシー、オフライン、API キー不要**に重心を移す
- Stage 3 と 4 は「降りる」動きではなく横移動です。ラダーの比喩が崩れているので、「同じ段に立ったままできること」として 1 章にまとめると流れが締まります。

### 3-3. 段（rung）と Stage の数え方が混乱
- "the Haiku three rungs up" とありますが、Haiku は Rung 2、Nova は Rung 3、Stage 5 はその下です。数え方次第では two rungs になります。
- Stage と Rung の二重番号も読者を迷わせます。

### 3-4. 冗長・口癖
- **"honest" / "honestly" が少なくとも 6 回**出てきます（Honest assessment, honestly not much, answer honestly, One honest trick, The honest limits, honest progress UI）。2 回までに減らすべきです。連発すると逆に信用を落とします。
- "What you give up / What you keep" の定型は良いので残します。ただし Rung 1 の "Honest assessment" は削れます。
- 結論の 5 項目は本文の再掲に近いので、3 行に圧縮できます。

### 3-5. オチのネタバレはサブタイトルだけではない
- イントロの番号リスト 5 項目目 "delete the server. Run the model in the visitor's browser and pay for static file delivery only." でも完全に明かしています。
- ヘッドラインを直すなら、ここも「5. And then a step that removes the ladder itself.」のように伏せる必要があります。
- 投稿先が目次を表示する場合は、**節見出しもネタバレ**になります。Stage 5 の "Delete the server — run the model in the browser" がそれです（article.md 版の "Step 7: Delete the server (CloudFront is the only bill)" と本文中の "Spoiler: the last step deletes the server." も同様）。

---

## 4. 事実確認が弱い箇所（出典）

| 主張 | 状態 | コメント |
|---|---|---|
| Opus 5.5 $4/$20、Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50（≤100K）、キャッシュ読み Opus $0.20 / Sonnet $0.10 | **Anthropic の first-party 価格と一致**（claude-api スキル参照資料、2026-11-03 キャッシュ） | ただし Anthropic 自身が「Bedrock の価格は別」と明記している。「Bedrock で確認済」と書かず「Anthropic list と一致、Bedrock の global は parity とされる」に留め、公開前に AWS の価格ページで照合する |
| Haiku 5.5 のキャッシュ読み $0.01 | [要確認] | 0.1 倍則からの推定と一致するが、一次情報は未確認 |
| Bedrock の regional endpoint は +10% | [要確認] | 二次情報のみ |
| Nova の価格（Lite $0.06/$0.24、Micro $0.035/$0.14） | [要確認] | 二次情報 3 件は**互いに独立とは限らない**（同じ元からのコピーの可能性）。「複数ソースが一致」は検証の代わりにならない |
| Nova のキャッシュ最小 1K トークン | **AWS ドキュメント（検索結果で確認）** | → Lever 1 の Nova 計算は不成立（1-3） |
| Lambda / DynamoDB / CloudFront の無料枠 | 公式で確認済（編集メモどおり） | DynamoDB はプロビジョンド前提の明記が必要 |
| Safari 18+ で WebGPU | **おそらく誤り（Safari 26）** | 1-10。二次情報ベース。macOS では以前から部分対応という記述もあるため Apple のリリースノートで要確認 |
| 「Bedrock で最も高価なモデル」 | **おそらく誤り** | 1-5（Fable 5.2） |
| The Frugal Architect の "frugal is not the same as cheap" | [要確認] | 引用風に書くなら原文の該当 law を特定する。言い換えなら「〜という趣旨」とする |
| WebLLM のモデルサイズ・VRAM | [要確認] | WebLLM の model list で確認 |
| Claude の思考トークンが出力課金になる点 | Anthropic ドキュメントで確認済 | 本文が完全に無視している（1-4） |
| Haiku 5.5 の新トークナイザ（同じ文で約 30% 多い） | Anthropic ドキュメントで確認済 | 「全モデル同じ 1,000/400 トークン」前提の注記が必要。Nova も別トークナイザ |

---

## 5. ヘッドライン候補（オチを明かさない）

方針は次のとおりです。
- "browser"、"WebLLM"、"CloudFront"、"$0"、"free"、"serverless/no server" は使わない
- 「最も高価」は 1-5 の理由で避ける
- 出発点の "$120" と「下り」の動きで引く

1. **The Frugal Chatbot: Starting at $120 a Month and Taking the Stairs Down**
   *Sub: I priced the same AWS support bot with Claude Opus first, then one step cheaper at a time, asking at every step what we actually gave up.*
   — 現タイトルを活かした最小変更案です。"taking the stairs" で下る旅が伝わり、どこまで降りるかは伏せられます。最も無難です。

2. **How Low Can a Chatbot Go? Pricing the Same AWS Bot from Opus Down**
   *Sub: Five versions of one support bot, one rung cheaper each time, until the question stops being "which model" and becomes something stranger.*
   — リンボーダンスの "how low can you go" を借りています。サブタイトルで「最後に問いの種類が変わる」と匂わせ、オチを伏せたまま続きを読ませます。

3. **$120, $60, $3… Where Does the Chatbot Bill Stop?**
   *Sub: Walking an AWS support bot down the model shelf, starting from the flagship, and keeping score of what each dollar was really buying.*
   — 数字の連なりそのものがフックです。末尾を伏せた数列で「次は？」と思わせます。SNS 映えは最も強いと思います。

4. **Start With the Best Model, Then Ask What It Buys You**
   *Sub: A frugal-architecture walk down the AWS model shelf: one chatbot, one fixed workload, and a price check at every step down.*
   — 教訓型です。The Frugal Architect の読者層に刺さる、落ち着いたトーンです。驚きは弱いですが、AWS Builder Center の真面目な読者には最も信頼されやすいと思います。

5. **The Downhill Chatbot: What You Lose (and Don't) Leaving the Flagship**
   *Sub: The same AWS support bot, rebuilt one rung cheaper at a time, measured against a fixed "good enough" bar, all the way to the bottom.*
   — "all the way to the bottom" で底があることだけを予告し、底の正体は伏せます。floor という判定基準が前面に出るので、3-1 の評価を入れた場合に最も映えます。

（番外）**Climbing Down From Opus** — 短く文学的です。"climb down" には「主張を引っ込める」という含みもあり、Opus は要らなかったかも、という皮肉が効きます。ただし Opus を知らない読者には伝わりません。

**推奨**: 3 か 1。3-1 の評価を追加するなら 5。

---

## 6. article.md（ディスク上の別バージョン）との対照

`~/frugal-chatbot/article.md`（11:16 更新、JS/Node 版、Step 1〜7 構成）は、貼り付けられたドラフトとは別の版です。この版は【重大】指摘の多くをすでに解決しています。正式ベースが貼り付け版であれば、**以下の部分は article.md から移植するのが最短**です。

| 指摘 | 貼り付け版 | article.md |
|---|---|---|
| 1-1 天井がトークン代を見ていない | 該当する | **解決済み**。トークン代込みで約 $249 / Opus なら約 $32,000 を計算し、DynamoDB の日次クォータ（コード付き）で約 $6 に抑え、Budgets は「alarm, not a brake」と明記 |
| 1-2 Lever 2 の「nearly $8」 | 該当する | **該当しない**（別の例：26,500 → 12,500 トークン） |
| 1-3 Nova キャッシュの 1K 最小 | 該当する | **解決済み**。1K 最小と TTL・夜間ミスを明記し、$1.29 は「大きな共有プレフィックスがある場合」と限定。ただし 6M/4M の表は 600 トークン前提のままで、注記と表の数字が整合しないのは残る |
| 1-4 temperature | 該当する | 該当しない（指定なし） |
| 1-4 スライス先頭が assistant | 該当する | **解決済み**（先頭の非 user を落とすコードあり） |
| 1-4 思考トークン | 無視している | **言及あり**（前提で除外を明記し、Step 1 で effort を下げて実測せよと書いている） |
| 1-4 入力長の上限 | なし | **あり**（`body.length > 8_000` を拒否） |
| 1-5 「最も高価」 | 該当する | **該当する**（"the most expensive model available"） |
| 1-10 Safari 18 | 該当する | 該当しない（"uneven" とぼかしている） |
| 1-10 WebLLM に FAQ がない | 該当する | **該当する** |
| 1-10 HF 依存 | 一言のみ | **より良い**（自前ホスト時の appConfig と約 $34/月の計算あり） |
| 3-1 floor 未検証 | 該当する | **該当する**（同様に断定） |
| 3-5 ネタバレ | サブタイトル＋リスト | **より強い**（サブタイトル、"Spoiler:" の一文、Step 7 の見出し） |

## 7. 優先度つき修正リスト

1. 天井節を「トークン予算の天井」に作り直す（1-1）
2. Lever 2 を $3.96 に修正（1-2）
3. Lever 1 の Nova 例を差し替える。1K 以上のプレフィックスに増やすか Haiku の例に置き換え、書き込みプレミアムとヒット率にも触れる（1-3）
4. Stage 1 のコードを修正する（temperature、スライス、effort、入力長の上限、モデル ID、タイムアウト）（1-4、1-7）
5. "most expensive/capable" と Safari 18 の誤りを直す（1-5、1-10）
6. floor の簡易評価を足すか、品質判定をトーンダウンする（3-1）
7. 規模の感度表と、Lever を上の段で見せる構成への組み替え（3-2）
8. ヘッドラインと、イントロのリスト 5 項目目のネタバレを伏せる（3-5、5）
