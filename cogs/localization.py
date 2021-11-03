localization = {
	"eng": {
		"language_not_available": {
			"description": 
				"This command isn't available in the language you selected. Continue?",
			"footer":
				"You can help translate NReader by visiting the support guild.",
			"button": 
				"Continue"
		},
		"language_options": {
			"english": 
				"English",
			"japanese":
				"Japanese",
			"chinese":
				"Chinese"
		},
		"general": {
			"not_nsfw": 
				"❌ This command cannot be used in a non-NSFW channel.",
		},

		"notifications_due": {
			"first_time_tip": {
				"title":
					"First Time Interaction Notification",
				"description":
					"👋 It appears to be your first time using this bot!\n"
					"🔞 This bot is to be used by mature users only and in NSFW channels.\n"
					"ℹ️ For more information and help, please use the `n!help` command.\n"
					"ℹ️ For brief legal information, please use the `n!legal` command.\n"
					"ℹ️ MechHub highly recommends you join the support server: **[MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n"
			},

			"lolicon_viewing_tip": 
				"Tip: To view restricted doujins on Discord, you need to invite me to a server that you own and run the `n!whitelist <'add' or 'remove'>` (Server-owner only) command. \n"
				"This will allow all users in your server to open restricted doujins.\n"
				"Restricted doujins are __only__ reflected on your history, favorites, bookmarks, or searches **in whitelisted servers**, but numerical statistics *may not* hide these ouside those domains."
		},

		"help": {
			"title": 
				"<:info:818664266390700074> Help",
			"description": 
				"**Search, overview, and read doujins in Discord.**\n" 
				"**Support server: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n" 
				"\n" 
				"For the full information sheet, visit [this Google Docs page](https://docs.google.com/document/d/e/2PACX-1vQAJRI5B8x0CP3ZCHjK9iZ8KQq3AGHEMwiBQL72Mwf1Zu6N2THedbAi1ThuB9iiuzcBv8ipt5_XfQf4/pub).\n"
				"\n"
				"Changing the bot language will also reset first time notifications.", 
			"footer": 
				"Provided by MechHub"
		},

		"invite": {
			"title": 
				"Invite NReader",
			"description": 
				"[Click Here]({url}) to invite NReader to your server!",
			"footer": 
				"Provided by MechHub"
		},

		"privacy": {
			# English only
		}, 

		"doujin_info": {
			"sfw":
				"Showing minimal information. Use the command in an NSFW-marked channel for more details.",
			"not_a_valid_id": 
				"❌ You didn't type a proper ID. Come on, numbers!",
			"doujin_not_found": 
				"🔎❌ I did not find a doujin with that ID.",
			"is_lolicon":
				"⚠️⛔ This doujin contains restricted tags and cannot be displayed publically.",
			"fields": {
				"not_provided":
					"Not provided",
				"original":
					"Original",

				"title": 
					"Title",

				"id/pages":
					"ID || Pages",

				"date_uploaded":
					"Date uploaded",
				"date_uploaded_weekdays": {
					0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
					4: "Thursday", 5: "Friday", 6: "Saturday"
				},
				"date_uploaded_format":
					"On {month_name} {day} ({weekday}), {year} at {hour}:{minute}{am_pm}",

				"languages":
					"Language(s) in this work",
				"language_names": {
					"translated": "Translated",
					"rewrite": "Rewritten",
					"speechless": "No dialogue",
					"japanese": "Japanese",
					"english": "English",
					"chinese": "Chinese",
					"cebuano": "Cebuano",
					"arabic": "Arabic",
					"javanese": "Javanese"
				},

				"artists":
					"Featured artist(s)",

				"characters":
					"Character(s) in this work",

				"parodies":
					"A parody of",

				"tags": 
					"Content tags",
				"tag_names": {},  # Translate a bunch of different common tags
			},

			"read": 
				"Read",
			"expand_thumbnail":
				"Expand Thumbnail",
			"minimize_thumbnail":
				"Minimize Thumbnail",
			"need_permissions":
				"Need Permissions",
			"unexpected_loss":
				"❌ Unexpected loss of required permissions.",
			"opened":
				"Opened"
		},

		"page_reader": { 
			"description": {
				"previous":
					"Previous",
				"next": 
					"Next",
				"finish":
					"**Finish**",
				"select":
					"Select",
				"stop":
					"Stop",
				"pause":
					"Pause",
				"bookmark":
					"Bookmark",
				"unbookmark":
					"Unbookmark"
			},
			"footer": 
				"Page [{current}/{total}] {bookmark}",
			"redirect_button":
				"Support Server",
			"init": {
				"description":
					"Waiting.",
				"footer":
					"Page [0/{total}]: Press ▶ Start to start reading.",
				"button":
					"Start",
			},
			"portal":
				"Click/Tap the mention above to jump to your reader.\n"
				"You opened `{code}`: `{name}`",
			"closing":
				"Closing...",
			"timeout":
				"You timed out on page [{current}/{total}].",
			"timeout_notification":
				"{mention}, you timed out in your doujin. Forgot to press pause?",
			"finished":
				"You finished this doujin.",
			"select_inquiry": {
				"description":
					"Enter a page number within 15 seconds, or type `n-cancel` to cancel.",
				"footer":
					"Bookmarked page: {bookmarked_page}",
			},
			"paused":
				"You paused this doujin.",
			"recall_saved": {
				"title":
					"Recall saved.",
				"description": 
					"Doujin `{code}` saved to recall to page [{current}/{total}].\n"
					"To get back to this page, run the `n!recall` command to instantly open a new reader starting on that page.",
			},
			"stopped":
				"You stopped reading this doujin.",
			"cannot_bookmark_first_page":
				"You cannot bookmark the first page. Use favorites instead!",
			"bookmarks_full":
				"❌ Your Bookmarks list is full. Please remove something from it to perform this action.",
			"favorites_full":
				"❌ Your Favorites list is full. Please remove something from it to perform this action.",
			"added_to_favorites":
				"✅ Added `{code}` to your favorites.",
			"removed_from_favorites":
				"✅ Removed `{code}` from your favorites.",
			"error":
				"An unhandled error occured; Please try again.\n"
				"If the issue persists, please try reopening the doujin.\n"
				"If reopening doesn't work, click the `Support Server` button."
		},

		"search_doujins": {
			
		},

		"recall": {
			
		},

		"popular": {
			
		},

		"lists": {
			
		},

		"search_appendage": {
		
		},

		"whitelist": {
			
		},

		"urban_dictionary": {
			# English only
		}

	},

	"jp": {
		"language_not_available": {
			"description": 
				"このコマンドは、ご使用の言語では使用できません。 継続する？",
			"footer": 
				"サポートギルドにアクセスすると、NReaderの翻訳を手伝うことができます。",
			"button": 
				"継続"
		},
		"language_options": {
			"english": 
				"英語",
			"japanese":
				"日本語",
			"chinese":
				"中国語"
		},

		"notifications_due": {
			"first_time_tip": {
				"title":
					"初回インタラクション通知",
				"description":
					"👋 ボットを初めて使用したようです！\n"
					"🔞 このボットは大人専用で、NSFWチャンネルでのみ使用できます。\n"
					"ℹ️ 詳細については、「`n!help`」コマンドを使用してください。 \n"
					"ℹ️ 英語の法律情報については、「`n!legal`」コマンドを使用してください。\n"
					"ℹ️ MechHubは、サポートギルドに参加することを強くお勧めします: **[MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n"
			},

			"lolicon_viewing_tip": 
				"ヒント：Discordで制限付き同人誌を表示するには、サーバーに招待して、「`n！whitelist <'add'または 'remove'>`」コマンドを実行します。"
                "これにより、サーバー上のすべてのユーザーが制限付き同人誌を開くことができます。\n"
                "制限付き同人誌は、ホワイトリストに登録されたサーバーでの履歴、お気に入り、ブックマーク、または検索にのみ反映されますが、数値統計ではこれらのドメインの外にそれらを隠すことはできません。"
		},

		"help": {
			"title": 
				"<:info:818664266390700074> 手助け",
			"description": 
				"**Discordで同人誌を検索、概要、読みます。**\n" 
				"**サポートギルド: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n" 
				"\n" 
				"すべての情報については、この[Googleドキュメント](https://docs.google.com/document/d/e/2PACX-1vSZkUzrO5sbwWJJPdejrn_Kl_HEsEqBjzTotcTmEI7bfcS8NDB4FDJnhEO2-avYCVuSMHThozw3H81b/pub)にアクセスしてください。\n"
				"\n"
				"ボットの言語を変更すると、初回の通知もリセットされます。",
			"footer": 
				"MechHubから提供された"
		},

		"invite": {
			"title": 
				"NReaderを招待する",
			"description": 
				"NReaderをギルドに招待するには、ここを[クリック]({url})してください。",
			"footer": 
				"MechHubから提供された"
		},

		"doujin_info": {
			"sfw":
				"最小限の情報を表示しています。 詳細については、NSFWでマークされたチャンネルでコマンドを使用してください。",
			"not_a_valid_id": 
				"❌ 識別は番号ではありません。 数字のみ！",
			"doujin_not_found": 
				"🔎❌ ボットは、そのIDを持つ同人誌を見つけることができませんでした。",
			"is_lolicon":
				"⚠️⛔ この同人誌には許可されていないタグがあり、表示できません。",
			"fields": {
				"not_provided":
					"提供されていない",
				"original":
					"オリジナル",

				"title": 
					"題名",

				"id/pages":
					"身元 || ページ",

				"date_uploaded":
					"アップロード日",
				"date_uploaded_weekdays": {
					0: "日", 1: "月", 2: "火", 3: "水",
					4: "木", 5: "金", 6: "土"
				},
				"date_uploaded_format":
					"{year}年{month_numeral}月{day}日（{weekday}）- {am_pm}{hour}:{minute}",

				"languages":
					"同人誌言語",
				"language_names": {
					"translated": "翻訳",
					"rewrite": "リライト",
					"speechless": "対話なし",
					"japanese": "日本語",
					"english": "英語",
					"chinese": "中国語",
					"cebuano": "セブアノ語",
					"arabic": "アラビア語",
					"javanese": "ジャワ語"
				},

				"artists":
					"同人誌アーティスト",

				"characters":
					"同人誌キャラクター",

				"parodies":
					"同人誌パロディー",

				"tags": 
					"コンテンツタグ",
				"tag_names": {},  # Translate a bunch of different common tags
			},

			"read": 
				"読む",
			"expand_thumbnail":
				"イ表紙画像を展開",
			"minimize_thumbnail":
				"表紙画像を最小化",
			"need_permissions":
				"必要な権限 ",
			"unexpected_loss":
				"❌ 必要な権限の予期しない喪失。",
			"opened":
				"開いた"
		},
		
		"page_reader": { 
			"description": {
				"previous":
					"前",
				"next": 
					"次",
				"finish":
					"**終了**",
				"select":
					"選択",
				"stop":
					"やめる",
				"pause":
					"一時停止",
				"bookmark":
					"ブックマーク",
				"unbookmark":
					"ブックマーク解除"
			},
			"footer": 
				"ページ [{current}/{total}] {bookmark}",
			"redirect_button":
				"サポートギルド",
			"init": {
				"description":
					"待っている。",
				"footer":
					"ページ [0/{total}]：▶スタートを押して読み始めます。",
				"button":
					"スタート",
			},
			"portal":
				"上記の説明をクリック/タップして、読者にジャンプしてください。\n"
				"「`{code}`」を開きました： `{name}` ",
			"closing":
				"閉鎖...",
			"timeout":
				"[{current} / {total}] ページでタイムアウトしました。",
			"timeout_notification":
				"{mention}, 同人誌でタイムアウトしました。一時停止を押すのを忘れましたか？",
			"finished":
				"あなたはこの同人誌を完成させました。",
			"select_inquiry": {
				"description":
					"15秒以内にページ番号を入力するか、「`n-cancel`」と入力してキャンセルしてください。",
				"footer":
					"ブックマークされたページ：{bookmarked_page}",
			},
			"paused":
				"この同人を一時停止しました。",
			"recall_saved": {
				"title":
					"保存されたリコール。",
				"description": 
					"コード「`{code}`」が保存された同人誌は、ページ[{current}/{total}]に呼び戻すことができます。\n"
					"このページに戻るには、「`n!recall`」コマンドを実行して、そのページから始まる新しいリーダーをすぐに開きます。",
			},
			"stopped":
				"あなたはこの同人誌を読むのをやめました。",
			"cannot_bookmark_first_page":
				"最初のページをブックマークすることはできません。代わりにお気に入りを使用してください！",
			"bookmarks_full":
				"❌ ブックマークリストがいっぱいです。このアクションを実行するには、ブックマークリストから何かを削除してください。",
			"favorites_full":
				"❌ お気に入りリストがいっぱいです。このアクションを実行するには、リストから何かを削除してください。",
			"added_to_favorites":
				"✅ お気に入りに「`{code}`」を追加しました。",
			"removed_from_favorites":
				"✅ お気に入りから` 「{code}」 `を削除しました。",
			"error":
				"未処理のエラーが発生しました。もう一度やり直してください。\n"
				"問題が解決しない場合は、同人誌を再度開いてみてください。\n"
				"再度開くことができない場合は、「サポートギルド」ボタンをクリックしてください。"
		}
	},

	"cn": {
		"language_not_available": {
			"description": 
				"此命令在您的语言中不可用。 你要继续吗？",
			"footer":
				"您可以通過訪問支持公會來幫助翻譯 NReader。",
			"button": 
				"继续"
		},
		"language_options": {
			"english": 
				"英語",
			"japanese":
				"日語",
			"chinese":
				"中文"
		},

		"notifications_due": {
			"first_time_tip": {
				"title":
					"首次互動通知",
				"description":
					"👋 看來你是第一次使用這個機器人！\n"
					"🔞 此機器人僅供成人使用，只能在 NSFW 頻道中使用。\n"
					"ℹ️ 如需更多信息，請使用 「`n!help`」 命令。\n"
					"ℹ️ 有關法律信息，請使用 「`n!legal`」 命令。\n"
					"ℹ️ MechHub 強烈推薦您加入支持公會：**[MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n"
			},

			"lolicon_viewing_tip": 
				"提示：要在 Discord 上查看受限制的漫畫，您需要邀請我加入您擁有的服務器並運行 「`n!whitelist <'add' or'remove'>`」 命令。\n"
				"這將允許您服務器上的所有用戶打開受限的同人圈。\n"
				"受限制的同人__僅__反映在您在**白名單服務器**上的歷史記錄、收藏夾、書籤或搜索中，但統計數據**可能不會**從這些域中隱藏此內容。"
		},

		"help": {
			"title": 
				"<:info:818664266390700074> 幫助",
			"description": 
				"**在 Discord 中搜索、概覽和閱讀同人。**\n" 
				"**支持公會: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n" 
				"\n" 
				"如需完整信息表，請訪問 [此 Google 文檔頁面](https://docs.google.com/document/d/e/2PACX-1vTszuOx36UbKmAhyX2sQ4jEJymmkyzf6oz-JduErnFxbWhoXoHeFEd0ZPv-VnKiUMFV4a_H8WjU1iPE/pub)。\n"
				"\n"
				"更改機器人語言也將重置首次通知。",
			"footer": 
				"由 MechHub 提供"
		},

		"invite": {
			"title": 
				"邀請 NReader",
			"description": 
				"[點擊這裡]({url})邀請這個機器人加入你的公會。",
			"footer": 
				"由 MechHub 提供"
		},

		"doujin_info": {
			"sfw": {
				"顯示最少的信息。 在 NSFW 標記的頻道中使用該命令以獲取更多詳細信息。"
			},
			"not_a_valid_id": 
				"❌ 標識無效。 只有數字！",
			"doujin_not_found": 
				"🔎❌ 那個漫畫不存在。",
			"is_lolicon":
				"⚠️⛔ 這本漫畫包含不允許的標籤。",
			"fields": {
				"not_provided":
					"無法使用",
				"original":
					"原來的",

				"title": 
					"標題",

				"id/pages":
					"鑑別 || 頁",

				"date_uploaded":
					"上傳日期",
				"date_uploaded_weekdays": {
					0: "星期日", 1: "星期一", 2: "星期二", 3: "星期三",
					4: "星期四", 5: "星期五", 6: "星期六"
				},
				"date_uploaded_format":
					"{year}年{month_numeral}月{day}日 ({weekday}) - {am_pm}{hour}:{minute}",  # 2006年1月29日

				"languages":
					"同人誌語言",
				"language_names": {
					"translated": "已翻譯",
					"rewrite": "又寫了",
					"speechless": "沒有對話",
					"japanese": "日語",
					"english": "英語",
					"chinese": "中文",
					"cebuano": "宿務語",
					"arabic": "阿拉伯語",
					"javanese": "爪哇語"
				},

				"artists":
					"同人誌藝人",

				"characters":
					"同人誌角色",

				"parodies":
					"同人誌模仿",

				"tags": 
					"內容標籤",
				"tag_names": {},  # Translate a bunch of different common tags
			},
			
			"read": 
				"讀",
			"expand_thumbnail":
				"展開圖片",
			"minimize_thumbnail":
				"最小化圖像",
			"need_permissions":
				"需要許可",
			"unexpected_loss":
				"❌ 所需的權限意外丟失。",
			"opened":
				"打開"
		},

		"page_reader": { 
			"description": {
				"previous":
					"以前的",
				"next": 
					"下一個",
				"finish":
					"**結束**",
				"select":
					"選擇",
				"stop":
					"停止",
				"pause":
					"暫停",
				"bookmark":
					"書籤",
				"unbookmark":
					"取消書籤"
			},

			"footer": 
				"頁面 [{current}/{total}] {bookmark}",
			"redirect_button":
				"支援公会",

			"init": {
				"description":
					"等待。",
				"footer":
					"頁面 [0/{total}]：按 ▶ 開始開始閱讀。",
				"button":
					"開始",
			},

			"portal":
				"單擊/點按上面提到的內容可跳轉到您的閱讀器。\n"
				"你打開了`{code}`：`{name}`",
			"closing":
				"關閉...",
			"timeout":
				"您在頁面 [{current}/{total}] 上超時。",
			"timeout_notification":
				"{mention}, 您在閱讀器中超時。忘記按暫停？",
			"finished":
				"你完成了這本漫畫。",
			"select_inquiry": {
				"description":
					"在 15 秒內輸入頁碼，或輸入「`n-cancel`」取消。",
				"footer":
					"書籤頁面：{bookmarked_page}",
			},
			"paused":
				"你暫停了這本漫畫。",
			"recall_saved": {
				"title":
					"召回已保存。",
				"description": 
					"保存了代碼「`{code}`」的漫畫，以回憶頁面 [{current}/{total}]。\n"
					"要返回此頁面，請運行「`n!recall`」命令以立即打開從該頁面開始的新閱讀器。",
			},
			"stopped":
				"你已經停止閱讀這本漫畫了。",
			"cannot_bookmark_first_page":
				"您不能為第一頁添加書籤。請改用收藏夾！",
			"bookmarks_full":
				"❌ 您的書籤列表已滿。請從中刪除某些內容以執行此操作。",
			"favorites_full":
				"❌ 您的收藏夾列表已滿。請從中刪除某些內容以執行此操作。",
			"added_to_favorites":
				"✅ 將「`{code}`」添加到您的收藏夾。",
			"removed_from_favorites":
				"✅ 您的收藏夾中刪除了「`{code}`」。",
			"error":
				"發生未處理的錯誤；請重試。\n"
				"如果問題仍然存在，請嘗試重新打開漫畫。\n"
				"如果重新打開不起作用，請單擊「支持公會」按鈕。"
		}
	}
}

from discord.ext.commands.cog import Cog

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Commands(bot))