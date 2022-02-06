'''
# Model串接Webcam的部分修改自: https://github.com/gabrielcassimiro17/raspberry-pi-tensorflow
# Author: Kuihao Chang, Rex, 黃晉澄
# Date: 2021/08/08 (Happy Father's Day!)
# Environment:
#   Python 3.9.6
#   pip 21.2.2
#   tensorflow 2.5.0
#   opencv-python 4.5.3.56
#   Pre-trained Model: EfficientDet-Lite2 (https://tfhub.dev/tensorflow/efficientdet/lite2/detection/1)
#   Dataset/Label: COCO 2017
# Notice:
#   (1) var Line_reminder_time 可控制 Line 提醒的週期，目前每 2 分鐘提醒一次
#   (2) 本程式正常的關閉方法:
#       a. 影像辨識: 點選影像辨識視窗 -> 英文輸入法，按下'q'鍵，視窗會正常關閉
#       b. 紀錄喝水的視窗: 直接點選 'x' 符號關閉即可
#       c. 當兩個視窗都關閉，程式會先自動關閉 Line 提醒功能，然後自動終止本程式 (含所有副程式)
#   (3) IFTTT key 將於 2021/8/13 報告結束後關閉，若想繼續使用本程式，請依雲端教學對 IFTTT 進行設定
#   (4) 關於關閉 Line 提醒執行緒的部分尚可優化，或用其他方式處理 Line 定時通知
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from tkinter import *

import tkinter.messagebox as msg
import argparse
import time
import cv2
import requests # for IFTTT request
import threading
import tensorflow as tf
import pandas as pd

'''
# Hyperparameter (重要的客製化控制參數)
'''
Threshold = 0.5 # Model predict score 的閥值
WAIT_TIME = 5.0 # Thread send to IFTTT 發送訊息的冷卻時間 (s)，即每喝水5秒蒐集一次數據
CAMERA_WIDTH = 640 # 相機解析度: 寬
CAMERA_HEIGHT = 480 # 相機解析度: 長
Deteck_window_name = 'Notice Water Drinking and Rest System: Drinking Detection' # OpenCV視窗標題
Frame_round = 0 # 迴圈執行次數統計 (=Frames數量)，用以控制Model執行inference的時間間隔
Line_reminder_time = 2 # [!!!] Line提醒的時間週期: 預設每 2 分鐘提醒一次 

Do_inference = True # 啟用 Model 推論
Abort = False # 強制終止程式運作

# RecordTable: dict() 紀錄辨識到的資訊
# [!!!] 注意: 此表建於全域，使執行緒也能共享記憶體
RecordTable = { 
                'last_send_timestamp':0.0, # 上次傳送資料的時間戳記
                'last_callThread_timestamp':0.0,
                'Person': list(), # 人的座標
                'P_timestamp': 0, # 紀錄人座標時的時間戳記
                'Bottle': list(), # 瓶子的座標
                'B_timestamp': 999, # 瓶子的座標時的時間戳記
                }

'''
# 以下為 Functions
'''
# for openCV window 
def nothing(x):
    pass

# post to IFTTT: 通知定時喝水
def send_Line(str1,str2,str3):
    LINE_event_name = 'Your IFTTT event name'
    '''Your IFTTT event name'''
    LINE_key = 'Your IFTTT key token'
    '''Your IFTTT key token'''
    # Your IFTTT LINE_URL with event name, key and json parameters (values)
    LINE_URL='https://maker.ifttt.com/trigger/' + LINE_event_name + '/with/key/' + LINE_key
    r = requests.post(LINE_URL, params={"value1":str1}
    #r = requests.post(LINE_URL, params={"value1":str1,"value2":str2,"value3":str3}
    )
    #print('Line通知發送結果:', r)
    print("*** Line提醒訊息已發送 ***")

# post to IFTTT: 僅新增喝水次數及時間
def send_Sheets(str1,str2,str3):
    SHEETS_event_name = 'Your IFTTT event name'
    '''Your IFTTT event name'''
    SHEETS_key = 'Your IFTTT key token'
    '''Your IFTTT key token'''
    # Your IFTTT LINE_URL with event name, key and json parameters (values)
    SHEETS_URL='https://maker.ifttt.com/trigger/' + SHEETS_event_name + '/with/key/' + SHEETS_key
    r = requests.post(SHEETS_URL, params={"value1":str1,"value2":str2,"value3":str3}) # 格式: 時間/喝水次數/水量
    #print('Sheet發送結果:', r)
    print("*** 喝水次數已上傳至 Google sheet ***")

# 將 timestamp (float) 轉換成 Datetime (string)
def TimeStampToStr(timestamp):
    struct_time = time.localtime(timestamp) # 轉成時間元組
    timeString = time.strftime("%Y-%m-%d %H:%M:%S", struct_time) # 轉成字串
    return timeString

# 喝水判斷
def CheckDrinking():
    global RecordTable # 取得全域紀錄表
    '''
    * 座標格式->list(): 0:ymin, 1:xmin, 2:ymax, 3:xmax
    * 先思考不會重疊的情況:
        A上 < B下 or A下 > B上 or A左 > B右 or A右 < B左 
    * 反之就一定重疊:
        A上 > B下 and A下 < B上 and A左 < B右 and A右 > B左 
    '''
    if ( # 檢查座標是否疊合: A上:ymin > B下:ymax
        ( RecordTable['Person'][0] < RecordTable['Bottle'][2] ) # 因為螢幕定義左上是 (0,0) 故又再相反
        # 檢查座標是否疊合: A下:ymax < B上:ymin
        and ( RecordTable['Person'][2] > RecordTable['Bottle'][0] ) # 因為螢幕定義左上是 (0,0) 故又再相反
        # 檢查座標是否疊合: A左:xmin < B右:xmax
        and ( RecordTable['Person'][1] < RecordTable['Bottle'][3] )
        # 檢查座標是否疊合: A右:xmax > B左:xmin
        and ( RecordTable['Person'][3] > RecordTable['Bottle'][1] )):
        print("正在喝水")
        return True
    else:
        print("沒有喝水")
        return False

# 上傳喝水次數 (由執行緒運行: IFTTT傳送)
def SendingIFTTT():
    global RecordTable # 取得全域紀錄表
    now_timestemp = time.time()
    print(f"現在時刻: {TimeStampToStr(now_timestemp)} 喝水次數+1 ヽ(・∀・)ﾉ")
    # Google Sheet 發送
    t_sheet_WaterPlus1 = threading.Thread(
        target = send_Sheets, 
        args = (TimeStampToStr(now_timestemp),1,''))
    t_sheet_WaterPlus1.start()
    # 更新發送時間
    RecordTable['last_send_timestamp'] = time.time()

'''
# 主程式
'''
def main():
    '''
    # 載入全域變數
    '''
    global Threshold
    global WAIT_TIME
    #global CAMERA_WIDTH
    #global CAMERA_HEIGHT
    global Deteck_window_name
    global Frame_round
    global Do_inference
    global RecordTable

    '''
    # CommandLine input args: 此只設定鏡頭指定的參數
    '''
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-v',
        '--video',
        help='Video number',
        required=False,
        type=int,
        default=0
    )
    args = parser.parse_args()

    '''
    # Load Model and Label
    '''
    detector = tf.keras.models.load_model('model')
    labels = pd.read_csv('labels.csv',sep=';',index_col='ID')
    labels = labels['OBJECT (2017 REL.)']

    '''
    # Set openCV camera
    '''
    cap = cv2.VideoCapture(args.video)
    # 更改畫面解析度
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    # 標題命名
    cv2.namedWindow(Deteck_window_name) # cv2.WINDOW_NORMAL
    # 增加 Trackbar 物件
    cv2.createTrackbar('Threshold %', Deteck_window_name, 0, 100, nothing)
    cv2.setTrackbarPos('Threshold %', Deteck_window_name, 50)

    '''
    # Main-loop (Camera recording) 
    '''
    while(True):
        # 拍下一張照片 (=影格 frame) # ret 代表成功與否 (True, False)
        ret, frame = cap.read()

        # 若允許執行 Model Inference
        if (Do_inference):
            # 調整frame numpy向量維度排列方式: BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 轉換成 Tensorflow 張量
            rgb_tensor = tf.convert_to_tensor(rgb_frame, dtype=tf.uint8)

            # Add dims to rgb_tensor
            rgb_tensor = tf.expand_dims(rgb_tensor , 0)
            
            # [!!!] Model Inference
            boxes = scores = classes = num_detections = None
            boxes, scores, classes, num_detections = detector(rgb_tensor)
            
            pred_labels = classes.numpy().astype('int')[0]
            pred_labels = [labels[i] for i in pred_labels]
            pred_boxes = boxes.numpy()[0].astype('int')
            pred_scores = scores.numpy()[0]
        
            '''
            # Sub-loop 
            # Drawing: 為畫面中的物件畫上Model的預測結果--方框、類別名稱、分數
            # Recording: 將偵測到的人、瓶子的Box座標及當下時間記錄起來
            '''
            img_boxes = None
            for score, (ymin,xmin,ymax,xmax), label in zip(pred_scores, pred_boxes, pred_labels):
                Threshold = cv2.getTrackbarPos('Threshold %',Deteck_window_name) / 100
                # 若分數小於 Threshold (閥值) 則不顯示方框，意思是該物件辨識信心水準過低
                if score < Threshold:
                    continue
                    
                score_txt = f'{100 * round(score,0)}' # 辨識分數 (to_String)
                img_boxes = cv2.rectangle(rgb_frame,(xmin, ymax),(xmax, ymin),(0,255,0),2) # cv2.rectangle() 直接為rgb_frame畫上方框，同時備份出 img_boxes     
                font = cv2.FONT_HERSHEY_SIMPLEX # 選用字型
                cv2.putText(img_boxes, label, (xmin, ymin+10), font, 1.0, (255,0,0), 3, cv2.LINE_AA) # 為img_boxes畫出類別
                cv2.putText(img_boxes, 'Score = '+ score_txt, (xmin, ymin+50), font, 0.6, (235,97,35), 2, cv2.LINE_AA) # 為img_boxes畫出分數

                # 有偵測到人就紀錄起來
                if label == 'person':
                    #print(f"是人類!!! {[ymin,xmin,ymax,xmax]}")
                    RecordTable['Person'] = [ymin,xmin,ymax,xmax]
                    RecordTable['P_timestamp'] = time.time()
                # 有偵測到瓶子就紀錄起來
                if label == 'bottle':
                    #print(f"是瓶子?!? {[ymin,xmin,ymax,xmax]}")
                    RecordTable['Bottle'] = [ymin,xmin,ymax,xmax]
                    RecordTable['B_timestamp'] = time.time()

            '''
            # [!!!] 呼叫一個執行緒(t_Check_and_Send)來判斷是否喝水、是否要傳送資料
            '''
            # 若相較上次發送資料的時間已經超過 WAIT_TIME，則可以進行判斷
            now_time = time.time()
            if ((now_time - RecordTable['last_send_timestamp'] > WAIT_TIME)
                and # 確定 person 與 bottle 的資料未過期 (兩者間隔不得大於 WAIT_TIME) 
                ( abs(RecordTable['B_timestamp'] - RecordTable['P_timestamp']) <= WAIT_TIME )
                and # 先出現人再出現瓶子
                ( RecordTable['B_timestamp'] >= RecordTable['P_timestamp'] )
                and # 檢查是否喝水
                CheckDrinking()
                and # 相較上次呼叫執行緒的時間間隔是否大過 WAIT_TIME
                (now_time - RecordTable['last_callThread_timestamp'] > WAIT_TIME)):
                #print("準備呼叫執行緒")
                RecordTable['last_callThread_timestamp'] = now_time
                t_Send = threading.Thread(target = SendingIFTTT)
                t_Send.start()
            
            # [!!!] 將frame numpy向量維度排列方式改回BGR順序
            if img_boxes is not None:
                bgr_frame = cv2.cvtColor(img_boxes, cv2.COLOR_RGB2BGR)
                cv2.imshow(Deteck_window_name, bgr_frame)
            else:
                # 若沒有辨識出東西就直接輸出原始畫面
                cv2.imshow(Deteck_window_name, frame)

        # 若不允許執行 Model inference 則直接輸出原始畫面
        else: 
            cv2.imshow(Deteck_window_name, frame)

        '''[降低系統負擔] 直接取消註解就能使用
        # 設定每 10 圈切換一次狀態: 連續 10 frame do inference <-> 連續 10 frame 休息
        Frame_round += 1
        if Frame_round  == 10: # 此調整要多久切換模式一次，單位為 while loop 圈數
            Frame_round = 0
            Do_inference = not(Do_inference)
        '''
        
        # for debug: 使鏡頭更新頻率降低
        #time.sleep(1/100)

        # openCV視窗的按鍵事件，已內建指派新的Thread控制，只會影響視窗本身的FPS，1表示視窗更新延遲1毫秒(ms)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 釋放鏡頭裝置(Capture)
    cap.release()
    # 關閉OpenCV視窗
    cv2.destroyAllWindows()

'''
# 副程式-1: 定時發送 Line 提醒喝水、休息
'''
def LineNotify(miunte):
    global Abort # 用來終止副程式
    NotifyDuration = float(miunte*60) # 單位改成秒
    print(f"*** Line 定時提醒功能已開啟: 每{miunte}分鐘會提醒您休息一次 ***")
    t_Timer = threading.currentThread() # [!!!] t_Timer 定時器執行緒，用來監控 while 迴圈的生死
    num = 1
    while getattr(t_Timer, 'alive', True) and not(Abort): # [!!!] getattr: 將 t_Timer 與自訂變數 alive=True 綁定，外部控制之用
        time.sleep(NotifyDuration) # [!!!] 正式使用時請將此「取消注解」
        t_send_line = threading.Thread(
            target = send_Line, 
            args = (f"\n目前工作已進入第{num}個{miunte}分鐘囉~ 喝個水，起來動動身子吧! (・∀・)",'',''))
        t_send_line.start()
        if t_send_line.is_alive(): t_send_line.join()
        num += 1

        # for debug: 立即結束此副程式 
        #if num == 3: break # [!!!] 正式使用時請將此「注解」
    print("*** 關閉Line定時提醒執行緒 ***")

'''
# 副程式-2: 紀錄喝水量的 GUI 介面，串聯上傳表單功能
'''
def Record_WaterVolume_GUI():
    # for GUI
    def record():
        SHEETS_event_name = 'Your IFTTT event name'
        '''Your IFTTT event name'''
        SHEETS_key = 'Your IFTTT key token'
        '''Your IFTTT key token'''
        try:
            if int(water.get()) > 0:
                now_time = time.time()
                cc = int(water.get())
                alertmsg.set("本次飲水量 " + str(int(cc)) + " cc")
                SHEETS_URL = 'https://maker.ifttt.com/trigger/' + SHEETS_event_name + '/with/key/' + SHEETS_key
                r = requests.post(SHEETS_URL, params={"value1": TimeStampToStr(now_time), "value2": '', "value3": str(int(cc))}) # 格式: 時間/喝水次數/水量
                #print(r)
            else:
                water.set("0")
                alertmsg.set("請輸入大於0的數字!")
        except:
            water.set("0")
            alertmsg.set("0cc")
            msg.showerror('輸入錯誤', '請輸入正確的數字!')

    # for GUI
    def clear():
        water.set("0")
        alertmsg.set("重新輸入")

    window = Tk()
    window.geometry("400x250")
    window.title("自動提醒喝水介面")
    window.config(bg="LightSkyBlue1")
    window.resizable(False, False)

    water = StringVar(None, "0")
    button1 = StringVar()
    button2 = StringVar()
    alertmsg = StringVar()

    label0 = Label(window, text="紀錄水量", font=("微軟正黑體", 18, "bold"), fg="gray29", bg="lightgoldenrod").pack(pady=30, side=TOP)

    label1 = Label(window, text="請輸入:", font=("微軟正黑體", 16, "bold"), fg='gray20', bg="LightSkyBlue1").place(x=60, y=98)

    entry1 = Entry(window, textvar=water, font=("微軟正黑體", 14), justify='center').place(x=145, y=100, width=80, height=30)

    label2 = Label(window, text="cc", font=("微軟正黑體", 16, "bold"), fg='gray20', bg="LightSkyBlue1").place(x=225, y=98)

    button1.set("確認")
    b1 = Button(window, textvar=button1, fg="IndianRed1", bg="gray88", font=("微軟正黑體", 12, "bold"), command=record)
    b1.place(x=265, y=100, height=30)

    button2.set("清除")
    b2 = Button(window, textvar=button2, fg="IndianRed1", bg="gray88", font=("微軟正黑體", 12, "bold"), command=clear)
    b2.place(x=320, y=100, height=30)

    alertmsg.set("本次飲水量 0 cc")
    message = Label(window, fg="gray35", bg="palegreen2", font=("微軟正黑體", 16, "bold"), textvar=alertmsg)
    message.pack(pady=55, side=BOTTOM)

    window.mainloop()

    print("*** Thread: GUI介面關閉 ***")
    global Abort, Line_reminder_time 
    Abort = True
    print(f"*** 本程式將於{Line_reminder_time}分鐘後自動關閉 (目前正在等待Line執行緒time.sleep結束)\n或著您可以直接呼叫工作管理員終止本程式 ***")

if __name__ == '__main__':
    '''
    # 副程式-1: 定時通知喝水、休息 (由執行緒 t_line_notify 負責)
    '''
    t_line_notify = threading.Thread(
        target = LineNotify, 
        args = (Line_reminder_time,))
    t_line_notify.start()

    '''
    # 副程式-2: 紀錄喝水量的 GUI 介面 (由執行緒 t_record_GUI 負責)
    '''
    t_record_GUI = threading.Thread(target = Record_WaterVolume_GUI)
    t_record_GUI.start()
    
    # 主程式: Webcam 喝水辨識及喝水紀錄自動上傳雲端
    main()
    
    # 停止Thread: t_line_notify
    t_line_notify.alive = False