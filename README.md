# Drinking-Reminder-System-For-Win10
A process which reminds drinking water regularly by LINE application and automatically detects, records the amount of water you drink.

---
## Demo video:
[![Demo-Video-Link](https://img.youtube.com/vi/YOUTUBE_VIDEO_ID_HERE/0.jpg)](https://drive.google.com/file/d/1VVBxfNuFTtg6hjWFq6CGRUjIahW3RCa8/view?usp=sharing)

## Highlight:
* LINE application reminds drinking water regularly
    * <img src="https://drive.google.com/uc?export=view&id=1C_vR2_AjIEtIojKMx7W-ZAhgw_FIgIo3" alt="LINE UI" height="500"/>
* Detects, records the amount of water you drink automatically
* Beautiful manual recording UI
    * ![manual recording UI](https://drive.google.com/uc?export=view&id=1Inp320YorAmIHLz7QB--ZAZwF4Dn638S)
* Drinking record in Google Sheet automatically

---
## Detail:
* 程式開發: Kuihao Chang, Rex, 黃晉澄 
* 檔案說明:
    1. 主程式: DrinkRestSys.py
        * 執行方法 1: python DrinkRestSys.py
        * 執行方法 2 (指定鏡頭裝置 default=0): python DrinkRestSys.py -v 0
    2. Pre-train Model (EfficientDet-Lite2): model (folder)
    3. Pre-train Model 的標籤: labels.csv
    4. IFTTT 設定: IFTTT_API_setting (folder)
* 必要安裝套件:
    1. Python 3.9.6
    2. pip 21.2.2
    3. tensorflow 2.5.0
    4. opencv-python 4.5.3.56
* 其他注意事項:
    1. var Line_reminder_time 可控制 Line 提醒的週期，目前每 2 分鐘提醒一次
    2. 本程式正常的關閉方法:<br>
        a. 影像辨識: 點選影像辨識視窗 -> 英文輸入法，按下'q'鍵，視窗會正常關閉<br>
        b. 紀錄喝水的視窗: 直接點選 'x' 符號關閉即可<br>
        c. 當兩個視窗都關閉，程式會先自動關閉 Line 提醒功能，然後自動終止本程式 (含所有副程式)<br>
    3. IFTTT key 將於 2021/8/13 報告結束後關閉，若想繼續使用本程式，請依雲端教學對 IFTTT 進行設定
    4. 關於關閉 Line 提醒執行緒的部分尚可優化，或用其他方式處理 Line 定時通知
* 參考來源:
    * Tensorflow 串接 Webcam 的程式片段修改自: https://github.com/gabrielcassimiro17/raspberry-pi-tensorflow
    * EfficientDet-Lite2: https://tfhub.dev/tensorflow/efficientdet/lite2/detection/1 
* licence: MIT
* Date: 2021/8/8
