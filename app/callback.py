# callback.py
import serial
import json
import time
import sys
import config as c

# ===== 문자열을 초(second)로 변환하는 맵핑 딕셔너리 =====
AMOUNT_MAP = {
    "LOW": 1.0,
    "MEDIUM": 2.0,
    "HIGH": 3.0
}
# =========================================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("MQTT 브로커에 성공적으로 연결되었습니다!")
        client.subscribe(c.MQTT_ORDER_TOPIC)
        print(f"토픽 구독 시작: {c.MQTT_ORDER_TOPIC}")
    else:
        print(f"MQTT 브로커 연결 실패, 에러 코드: {reason_code}")
        if c.ser and c.ser.is_open:
            c.ser.close()
        sys.exit(1)

def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode('utf-8', errors='ignore').strip()
    print(f"\n--- MQTT 메시지 수신 ---")
    print(f"토픽: {msg.topic}")
    print(f"원본 메시지: '{raw_payload}'")
    print(f"---------------------------\n")

    try:
        data = json.loads(raw_payload)
        
        # ----------------------------------------------------
        # 1. 컵 디스펜서 명령 강제 실행 및 우선 순위 확보
        # ----------------------------------------------------
        CUP_COMMAND_PREFIX = "U"     
        # 컵 디스펜서 작동 시간 3.0초로 고정
        CUP_DISPENSE_TIME = 3.0      
        # 컵이 떨어지기를 기다리는 지연 시간
        CUP_POST_DELAY = 5.0         
        
        cup_command_to_send = f"{CUP_COMMAND_PREFIX}{CUP_DISPENSE_TIME}"
        
        print(f"\n--- 컵 디스펜서 강제 실행 (우선) ---")
        print(f">> [강제 설정] 컵 작동 시간은 {CUP_DISPENSE_TIME}초로 고정됩니다.")
        
        try:
            c.ser.write(cup_command_to_send.encode())
            print(f"아두이노로 컵 명령 전송 완료: '{cup_command_to_send}'")
            print(f"-> 다른 재료 명령 전송까지 {CUP_POST_DELAY}초 대기 중...")
            time.sleep(CUP_POST_DELAY) 
            
        except serial.SerialException as e:
            print(f"아두이노로 컵 명령 전송 실패: {e}")
            return 

        # ----------------------------------------------------
        # 2. 나머지 재료 분배 명령 순회 및 전송 (물 용량 조절 기능 복구)
        # ----------------------------------------------------
        for ingredient, value_to_send in data.items():
            command_prefix = None
            duration = None
            
            if ingredient == "cup":
                continue 

            # ===== 명령 접두사 설정 =====
            if ingredient == "water":
                command_prefix = "W"
            elif ingredient == "sugar":
                command_prefix = "S"
            elif ingredient == "coffee":
                command_prefix = "C"
            elif ingredient == "iced_tea":
                command_prefix = "I"
            elif ingredient == "green_tea":
                command_prefix = "G"

            if command_prefix:
                # ===== [수정] 문자열을 초(second)로 변환하는 로직 (물 포함) =====
                if isinstance(value_to_send, str):
                    value_upper = value_to_send.upper()
                    duration = AMOUNT_MAP.get(value_upper)
                    
                # 숫자로 값이 넘어왔을 경우
                elif isinstance(value_to_send, (int, float)) and value_to_send > 0:
                    duration = value_to_send
                # =============================================================

            # --- 명령 전송 ---
            if command_prefix and duration is not None and duration > 0:
                command_to_send = f"{command_prefix}{duration}"
                print(f"아두이노로 전송할 명령: '{command_to_send}' (변환된 시간: {duration}s)")
                
                try:
                    c.ser.write(command_to_send.encode())
                    print(f"아두이노로 전송 완료 ('{ingredient}'): '{command_to_send}'")
                except serial.SerialException as e:
                    print(f"아두이노로 전송 실패: {e}")
            elif command_prefix:
                print(f"경고: 재료 '{ingredient}'의 값 '{value_to_send}'이 유효하지 않거나 변환할 수 없습니다. 명령을 건너뜕니다.")

    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패 - {e}")
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")