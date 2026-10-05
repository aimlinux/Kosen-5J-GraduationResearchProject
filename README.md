# Kosen-5J-GraduationResearchProject

## 冷蔵庫 IoT 状態モニター

アプリ本体は `fridge_iot_app/` にあります。起動方法・API仕様は [fridge_iot_app/README.md](fridge_iot_app/README.md) を参照してください。

```text
Kosen-5J-GraduationResearchProject/
├── README.md
└── fridge_iot_app/
	├── app.py                 # FastAPIアプリ、API、SQLite保存
	├── requirements.txt       # Python依存ライブラリ
	├── README.md              # 起動方法とAPI仕様
	├── fridge_data.sqlite3    # 起動時に作成される計測データベース
	└── static/
		├── index.html         # ダッシュボード
		├── style.css          # 画面スタイル
		└── app.js             # API連携とグラフ描画
```