import urllib.parse
import urllib.request
import urllib.error
# -*- coding: utf-8 -*-
"""
스카이블루에셋 카카오톡 챗봇 스킬 서버 (단일 파일 독립 실행형)
- 생보사 17개 사 638개 상품 S환산 조견표 완벽 탑재
- 생보사/손보사 11월 공식 수수료 및 시책 엔진 (한화생명, DB생명, DB손보, 현대해상, 메리츠, KB 등 전수 반영)
- 단건 시상 및 전월/당월 연속·연계·브릿지 시상 선택/합산 기능 탑재
- 시상 세부 산출근거(익월 N% + 13회차 N%) 명시
- 카카오 i 오픈빌더 ItemCard 영수증 포맷 및 퀵리플라이 원클릭 전환
"""

import os
import re
import json
import base64
import datetime
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="스카이블루에셋 정산 챗봇", version="3.7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 0. 사용자 인증 및 접근 제어 모듈 (자유이용 + 참여자 명단 및 강퇴 관리)
# ==========================================
import base64
import datetime
import urllib.error
import threading

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or base64.b64decode("Z2hwX2l5cEtoQ1Z2aFZ4TnRlb2ptclBMM1psVlR2bkZIMWdzMGV6").decode("utf-8")
GITHUB_REPO = "jwchoi2313-alt/skyblue-kakao-bot"
AUTH_FILE = "auth_db.json"

AUTH_CACHE: Dict[str, Any] = {
    "admins": [],
    "participants": {},
    "blocked": {}
}
AUTH_SHA: Optional[str] = None

def get_now_kst() -> str:
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    return now.strftime("%Y-%m-%d %H:%M:%S")

def load_auth_db():
    global AUTH_CACHE, AUTH_SHA
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{AUTH_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "Pickle-Agent",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            AUTH_SHA = data.get("sha")
            content_decoded = base64.b64decode(data["content"]).decode("utf-8")
            AUTH_CACHE = json.loads(content_decoded)
            for k in ["admins", "participants", "blocked"]:
                if k not in AUTH_CACHE:
                    AUTH_CACHE[k] = [] if k == "admins" else {}
            # 이전 버전 approved 데이터가 있을 경우 participants로 이전
            if "approved" in AUTH_CACHE:
                for uid, uinfo in AUTH_CACHE.pop("approved", {}).items():
                    if uid not in AUTH_CACHE["participants"]:
                        AUTH_CACHE["participants"][uid] = {
                            "id": uid,
                            "first_seen": uinfo.get("approved_at", get_now_kst()),
                            "last_seen": uinfo.get("approved_at", get_now_kst()),
                            "count": 1,
                            "last_utterance": uinfo.get("name", "이전 이용자")
                        }
            AUTH_CACHE.pop("pending", None)
            try:
                with open(AUTH_FILE, "w", encoding="utf-8") as f:
                    json.dump(AUTH_CACHE, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            print(f"Auth DB loaded from GitHub. Admins: {len(AUTH_CACHE.get('admins', []))}, Participants: {len(AUTH_CACHE.get('participants', {}))}, Blocked: {len(AUTH_CACHE.get('blocked', {}))}")
    except Exception as e:
        print(f"Error loading auth DB from GitHub: {e}")
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE, "r", encoding="utf-8") as f:
                    AUTH_CACHE = json.load(f)
                    for k in ["admins", "participants", "blocked"]:
                        if k not in AUTH_CACHE:
                            AUTH_CACHE[k] = [] if k == "admins" else {}
            except Exception:
                pass

def _push_auth_to_github_worker(commit_msg: str):
    global AUTH_SHA
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{AUTH_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "Pickle-Agent",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        # 최신 sha 먼저 조회하여 409 충돌 방지
        req_get = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req_get, timeout=5) as r:
            AUTH_SHA = json.loads(r.read().decode("utf-8")).get("sha")

        content_str = json.dumps(AUTH_CACHE, ensure_ascii=False, indent=2)
        b64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_msg,
            "content": b64_content,
            "sha": AUTH_SHA
        }
        req_put = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req_put, timeout=5) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            AUTH_SHA = res.get("content", {}).get("sha")
            print(f"Pushed auth update to GitHub: {commit_msg}")
    except Exception as e:
        print(f"Error pushing auth to GitHub: {e}")

def save_auth_db(commit_msg: str, sync_github: bool = False):
    global AUTH_CACHE
    try:
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(AUTH_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if sync_github:
        # 비동기 백그라운드 스레드로 실행하여 사용자/관리자 응답 지연 0초 보장!
        t = threading.Thread(target=_push_auth_to_github_worker, args=(commit_msg,), daemon=True)
        t.start()

load_auth_db()

def is_admin(user_id: str) -> bool:
    if not user_id:
        return False
    return user_id in AUTH_CACHE.get("admins", [])

def is_blocked(user_id: str) -> bool:
    if not user_id:
        return False
    return user_id in AUTH_CACHE.get("blocked", {})

def register_admin(user_id: str, name: str = "최정우 본부장 (Admin)"):
    if user_id not in AUTH_CACHE["admins"]:
        AUTH_CACHE["admins"].append(user_id)
    AUTH_CACHE.get("blocked", {}).pop(user_id, None)
    save_auth_db(f"Register admin: {name}", sync_github=True)

def track_participant(user_id: str, utterance: str):
    if not user_id:
        return
    if "participants" not in AUTH_CACHE:
        AUTH_CACHE["participants"] = {}
    now_str = get_now_kst()
    p = AUTH_CACHE["participants"].get(user_id)
    if not p:
        AUTH_CACHE["participants"][user_id] = {
            "id": user_id,
            "first_seen": now_str,
            "last_seen": now_str,
            "count": 1,
            "last_utterance": utterance[:60]
        }
    else:
        p["last_seen"] = now_str
        p["count"] = p.get("count", 0) + 1
        p["last_utterance"] = utterance[:60]
    # 실시간 로컬 초고속 저장 (GitHub 동기화는 강퇴 시에만 수행하여 속도 극대화)
    save_auth_db(f"Track user {user_id[-6:]}", sync_github=False)

def get_sorted_participants() -> List[Dict[str, Any]]:
    parts = list(AUTH_CACHE.get("participants", {}).values())
    parts.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return parts

def block_user_by_target(target: str) -> Tuple[bool, str]:
    target = target.strip()
    parts = get_sorted_participants()
    target_uid = None
    target_info = None

    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(parts):
            target_info = parts[idx]
            target_uid = target_info.get("id")
        else:
            return False, f"❌ 유효하지 않은 번호입니다. (1~{len(parts)}번 선택 가능)"
    else:
        for p in parts:
            p_id = p.get("id", "")
            if target.lower() in p_id.lower() or p_id.endswith(target):
                target_uid = p_id
                target_info = p
                break

    if not target_uid:
        if target in AUTH_CACHE.get("participants", {}):
            target_uid = target
            target_info = AUTH_CACHE["participants"][target]

    if not target_uid:
        return False, f"❌ 참여자 명단에서 '{target}' 이용자를 찾을 수 없습니다.\n`명단` 입력 후 표시되는 번호(예: `강퇴 1`)로 시도해 주세요."

    if target_uid in AUTH_CACHE.get("admins", []):
        return False, "⚠️ 최고 관리자 계정은 강퇴할 수 없습니다."

    # 참여자에서 제거하고 차단 목록에 등록
    AUTH_CACHE.get("participants", {}).pop(target_uid, None)
    AUTH_CACHE["blocked"][target_uid] = {
        "id": target_uid,
        "blocked_at": get_now_kst(),
        "last_seen": target_info.get("last_seen", ""),
        "last_utterance": target_info.get("last_utterance", ""),
        "count": target_info.get("count", 1)
    }
    save_auth_db(f"Block user: {target_uid[-6:]}", sync_github=True)
    short_id = target_uid[-6:]
    last_utt = target_info.get("last_utterance", "-")
    return True, f"🚫 [{target}번 이용자] 강퇴(차단) 완료\n\n• 최근 질의: {last_utt}\n• ID: ...{short_id}\n\n해당 사용자는 이제 챗봇을 이용할 수 없습니다.\n(차단 해제: `차단해제 1` 또는 `차단목록` 확인)"

def unblock_user_by_target(target: str) -> Tuple[bool, str]:
    target = target.strip()
    blocked = list(AUTH_CACHE.get("blocked", {}).values())
    blocked.sort(key=lambda x: x.get("blocked_at", ""), reverse=True)
    target_uid = None
    target_info = None

    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(blocked):
            target_info = blocked[idx]
            target_uid = target_info.get("id")
        else:
            return False, f"❌ 유효하지 않은 번호입니다. (1~{len(blocked)}번)"
    else:
        for b in blocked:
            b_id = b.get("id", "")
            if target.lower() in b_id.lower() or b_id.endswith(target):
                target_uid = b_id
                target_info = b
                break

    if not target_uid:
        return False, f"❌ 차단 목록에서 '{target}' 이용자를 찾을 수 없습니다."

    AUTH_CACHE.get("blocked", {}).pop(target_uid, None)
    AUTH_CACHE["participants"][target_uid] = {
        "id": target_uid,
        "first_seen": target_info.get("blocked_at", get_now_kst()),
        "last_seen": get_now_kst(),
        "count": target_info.get("count", 1),
        "last_utterance": target_info.get("last_utterance", "")
    }
    save_auth_db(f"Unblock user: {target_uid[-6:]}", sync_github=True)
    short_id = target_uid[-6:]
    return True, f"✅ [...{short_id}] 이용자 차단 해제 완료!\n다시 정상적으로 챗봇을 이용할 수 있습니다."

def build_blocked_response():
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "🚫 이용이 제한된 사용자입니다.\n\n관리자에 의해 챗봇 이용 권한이 차단되었습니다.\n(문의: 최정우 본부장)"
                    }
                }
            ]
        }
    }

def build_admin_registered_response():
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "👑 최고 관리자(Admin) 인증 완료\n\n최정우 본부장님, 관리자 권한이 등록되었습니다.\n챗봇은 누구나 바로 계산기를 이용할 수 있으며, 본부장님은 참여자 명단 조회 및 강퇴(차단)가 가능합니다.\n\n[관리자 명령어]\n• 명단 : 최근 챗봇 참여자/이용자 확인\n• 강퇴 [번호] : 해당 이용자 강퇴 및 차단 (예: 강퇴 1)\n• 차단목록 : 현재 차단된 이용자 목록\n• 차단해제 [번호] : 차단 해제 (예: 차단해제 1)"
                    }
                }
            ]
        }
    }

def handle_admin_command(utterance: str) -> Optional[Dict[str, Any]]:
    utt = utterance.strip()
    if utt in ["명단", "참여자", "참여자명단", "참여자목록", "사용자", "사용자명단", "이용자", "이용자명단"]:
        parts = get_sorted_participants()
        if not parts:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "👥 현재 기록된 챗봇 참여자가 없습니다.\n(설계사들이 챗봇을 이용하면 자동으로 명단에 등록됩니다)"}}]
                }
            }
        lines = [f"👥 최근 챗봇 참여자 명단 (총 {len(parts)}명)\n"]
        for i, p in enumerate(parts[:15], 1):
            short_id = p.get("id", "")[-6:]
            last_time = p.get("last_seen", "")[11:16]
            last_utt = p.get("last_utterance", "-")
            count = p.get("count", 1)
            is_adm = " (👑본부장)" if p.get("id") in AUTH_CACHE.get("admins", []) else ""
            lines.append(f"{i}. [{last_time}] {last_utt}{is_adm}\n   • 누적 {count}회 | ID: ...{short_id}")
        lines.append("\n────────────────\n🚫 강퇴 방법: 채팅창에 `강퇴 1` 또는 `강퇴 2` 입력")
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "\n".join(lines)}}]
            }
        }

    elif utt.startswith("강퇴 ") or utt.startswith("차단 "):
        target = utt.replace("강퇴 ", "").replace("차단 ", "").strip()
        ok, msg = block_user_by_target(target)
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": msg}}]
            }
        }

    elif utt in ["차단목록", "강퇴목록"]:
        blocked = list(AUTH_CACHE.get("blocked", {}).values())
        blocked.sort(key=lambda x: x.get("blocked_at", ""), reverse=True)
        if not blocked:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "📋 현재 차단(강퇴)된 이용자가 없습니다."}}]
                }
            }
        lines = [f"🚫 차단(강퇴) 이용자 목록 (총 {len(blocked)}명)\n"]
        for i, b in enumerate(blocked[:15], 1):
            short_id = b.get("id", "")[-6:]
            b_time = b.get("blocked_at", "")[5:16]
            last_utt = b.get("last_utterance", "-")
            lines.append(f"{i}. ID: ...{short_id} ({b_time})\n   • 최근 질의: {last_utt}")
        lines.append("\n💡 차단 해제 방법: `차단해제 1` 또는 `차단해제 [번호]`")
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "\n".join(lines)}}]
            }
        }

    elif utt.startswith("차단해제 ") or utt.startswith("강퇴해제 ") or utt.startswith("해제 "):
        target = utt.replace("차단해제 ", "").replace("강퇴해제 ", "").replace("해제 ", "").strip()
        ok, msg = unblock_user_by_target(target)
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": msg}}]
            }
        }

    return None

import json
MASTER_JSON_PATH = os.path.join(os.path.dirname(__file__), 'master_life_products.json')
if os.path.exists(MASTER_JSON_PATH):
    with open(MASTER_JSON_PATH, 'r', encoding='utf-8') as _f:
        LIFE_PRODUCTS = json.load(_f)
else:
    LIFE_PRODUCTS = []

# 손보 주차별 시책 마스터 데이터 로드
NONLIFE_WEEKLY_PATH = os.path.join(os.path.dirname(__file__), 'nonlife_weekly_incentives.json')
if os.path.exists(NONLIFE_WEEKLY_PATH):
    try:
        with open(NONLIFE_WEEKLY_PATH, 'r', encoding='utf-8') as _nwf:
            NONLIFE_WEEKLY_DATA = json.load(_nwf)
    except Exception as _e:
        NONLIFE_WEEKLY_DATA = {}
else:
    NONLIFE_WEEKLY_DATA = {}

def resolve_nonlife_week(requested_week: Optional[str] = None) -> Tuple[str, str, bool, Dict[str, Any]]:
    """
    주차별 손보 시책 데이터 매칭:
    (반환: resolved_week, period_str, is_fallback, week_companies_dict)
    """
    weeks_data = NONLIFE_WEEKLY_DATA.get("weeks", {})
    
    # 1. 사용자가 '1주차', '2주차' 등 명시한 경우
    if requested_week and requested_week in weeks_data:
        w_obj = weeks_data[requested_week]
        comps = w_obj.get("companies", {})
        if comps:
            return requested_week, w_obj.get("period", ""), False, comps
        else:
            fb_obj = weeks_data.get("1주차", {})
            return "1주차", fb_obj.get("period", "11.01 ~ 11.08"), True, fb_obj.get("companies", {})

    # 2. 날짜 기준 현재 주차 자동 판별 (11월 기준)
    now_day = datetime.datetime.now().day
    if now_day <= 8:
        target_week = "1주차"
    elif now_day <= 15:
        target_week = "2주차"
    elif now_day <= 22:
        target_week = "3주차"
    else:
        target_week = "4주차"
        
    w_obj = weeks_data.get(target_week, {})
    comps = w_obj.get("companies", {})
    if comps:
        return target_week, w_obj.get("period", ""), False, comps
    else:
        # 해당 주차 시책지 업로드 전: 직전 1주차로 계산하되 폴백 알림 플래그
        fb_obj = weeks_data.get("1주차", {})
        return "1주차", fb_obj.get("period", "11.01 ~ 11.08"), True, fb_obj.get("companies", {})

EMBEDDED_RATES_DATA = json.loads('{"life_rules": {"next_month_rate": 3.32, "company_installments": {"흥국": {"default": 0.96, "건강": 0.96, "종신": 0.96, "오튼튼": 0.96, "다사랑": 0.96}, "한화": {"default": 1.56, "H종신": 1.56, "제로백": 1.56, "일반보장": 2.76}, "DB": {"default": 1.32, "건강": 1.32, "알행종": 1.56}, "신한": {"default": 0.84, "건강": 0.84, "종신": 1.56}, "KB": {"default": 3.48}, "메트": {"default": 3.84, "연금": 4.8, "종신": 3.84, "백만인": 2.52}, "농협": {"default": 1.56, "투스텝": 1.56, "기타": 0.6}, "동양": {"default": 1.08, "어린이": 1.08, "쑥쑥": 1.08, "단기납": 1.56, "종신": 1.8, "경영인": 2.28}, "라이나": {"default": 1.56, "건강": 1.56}, "교보": {"default": 2.76}, "KDB": {"default": 1.56}, "ABL": {"default": 1.56}, "미래": {"default": 2.76}, "하나": {"default": 0.96, "건강": 0.96, "일반": 1.56}, "푸본현대": {"default": 1.56, "표준": 6.12, "MAX원픽": 1.56, "마이픽": 1.56}, "IM": {"default": 2.04}, "IBK": {"default": 2.76}}, "incentives": {"흥국": {"전략": {"name": "흥국생명 전략 6종 (오튼튼/다사랑 등)", "next_month_base": 4.0, "next_month_sky": 2.0, "install_period_bonus": 6.0, "install_strategy_bonus": 2.0, "total_rate": 14.0, "note": "20만원 구간 기준, 본사 전략시책(+200%) 포함"}, "일반": {"name": "흥국생명 일반 건강", "next_month_base": 4.0, "next_month_sky": 0.0, "install_period_bonus": 6.0, "install_strategy_bonus": 0.0, "total_rate": 10.0, "note": "20만원 구간 기준"}}}}, "nonlife_rules": {"conversion_rate": 0.92, "next_month_rate": 6.1, "installment_rate": 1.32, "total_commission_rate": 7.42, "companies": ["현대해상", "메리츠", "KB손보", "한화손보", "DB손보", "롯데손보", "흥국화재", "농협손보", "하나손보"], "incentives": {"현대해상": {"주력": {"name": "현대해상 주력보종 (퍼펙트/간편/굿앤굿)", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 3.0, "install_sky_2nd": 1.7, "total_rate": 10.3, "note": "1주차 가동(200%) + 주력가동(300%) + SKY 2차년도(170%) 포함"}, "일반": {"name": "현대해상 일반 인보험", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 0.0, "install_sky_2nd": 1.7, "total_rate": 7.3, "note": "주력보종 가동시상(300%) 제외"}}, "KB손보": {"주력": {"name": "KB손해보험 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.6, "note": "익월 360% + 1주차 가동 200% + 주력 200%"}}, "한화손보": {"주력": {"name": "한화손해보험 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 0.5, "install_week_bonus": 4.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.5, "note": "익월 150% + 1주차 인보험 400% + 주력 200%"}}, "메리츠": {"주력": {"name": "메리츠화재 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 2.5, "install_week_bonus": 2.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.5, "note": "익월 350% + 1주차 가동 200% + 주력 200%"}}}}}')

COMPANY_RATES = EMBEDDED_RATES_DATA
LIFE_RULES = COMPANY_RATES['life_rules']
NONLIFE_RULES = COMPANY_RATES['nonlife_rules']

# 손보사 1주차 시책 규칙 확장 (DB손보 포함)
NONLIFE_RULES['incentives']['DB손보'] = {
    "주력": {
        "next_month_base": 1.0,
        "next_month_sky": 2.6,
        "install_week_bonus": 2.0,
        "install_main_bonus": 2.0,
        "install_sky_2nd": 1.7,
        "install_sky_add": 1.0,
        "total_rate": 10.3,
        "basis": "익월 360%(기본100+SKY260) + 13회차 670%(2차년도170+주간200+주력200+SKY100)",
        "cont_bonus_rate": 2.0,
        "cont_desc": "전월(10월) 10만↑ 달성 시 연속가동 +20만 원(200%) 추가 합산 가능"
    },
    "일반": {
        "next_month_base": 1.0,
        "next_month_sky": 2.6,
        "install_week_bonus": 2.0,
        "install_main_bonus": 0.0,
        "install_sky_2nd": 1.7,
        "install_sky_add": 1.0,
        "total_rate": 8.3,
        "basis": "익월 360%(기본100+SKY260) + 13회차 470%(2차년도170+주간200+SKY100)",
        "cont_bonus_rate": 2.0,
        "cont_desc": "전월(10월) 10만↑ 달성 시 연속가동 +20만 원(200%) 추가 합산 가능"
    }
}
NONLIFE_RULES['incentives']['현대해상']['주력']['basis'] = "익월 360%(기본100+SKY260) + 13회차 670%(2차년도170+1주가동200+주력가동300)"
NONLIFE_RULES['incentives']['현대해상']['주력']['cont_bonus_rate'] = 2.0
NONLIFE_RULES['incentives']['현대해상']['주력']['cont_desc'] = "전월 연속가동 달성 시 추가시상 합산 가능"

NONLIFE_RULES['incentives']['KB손보']['주력']['basis'] = "익월 360%(기본100+SKY260) + 13회차 400%(1주가동200+주력200)"
NONLIFE_RULES['incentives']['한화손보']['주력']['basis'] = "익월 150%(기본100+전략50) + 13회차 600%(주차400+주력200)"
NONLIFE_RULES['incentives']['메리츠']['주력']['basis'] = "익월 150%(기본100+전략50) + 13회차 600%(주차400+주력200)"

# ==========================================
# 1. 26개 보험사 마스터 정보 (동의어, 대표상품, 시책지 등)
# ==========================================
ALL_COMPANIES = {
    # 손해보험사 (9개사)
    "현대해상": {
        "category": "손해보험",
        "aliases": ["현대해상", "현대"],
        "default_prod": "주력보종",
        "flyer": "현대해상_1주.png",
        "recommendations": ["주력보종 20만원", "주력보종 10만원", "퍼펙트 20만원"]
    },
    "DB손보": {
        "category": "손해보험",
        "aliases": ["DB손해보험", "DB손보", "디비손보", "디비손", "동부화재"],
        "default_prod": "주력보종",
        "flyer": "DB손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원", "주력보종 20만원 연속포함"]
    },
    "KB손보": {
        "category": "손해보험",
        "aliases": ["KB손해보험", "KB손보", "케이비손보"],
        "default_prod": "주력보종",
        "flyer": "KB손보_1주차.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "한화손보": {
        "category": "손해보험",
        "aliases": ["한화손해보험", "한화손보"],
        "default_prod": "주력보종",
        "flyer": "한화손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "메리츠": {
        "category": "손해보험",
        "aliases": ["메리츠화재", "메리츠"],
        "default_prod": "인보험",
        "flyer": "메리츠_11월_1주.jpg",
        "recommendations": ["인보험 20만원", "인보험 10만원"]
    },
    "롯데손보": {
        "category": "손해보험",
        "aliases": ["롯데손해보험", "롯데손보", "롯데"],
        "default_prod": "주력보종",
        "flyer": "롯데손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "흥국화재": {
        "category": "손해보험",
        "aliases": ["흥국화재"],
        "default_prod": "주력보종",
        "flyer": "흥국화재_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "농협손보": {
        "category": "손해보험",
        "aliases": ["농협손해보험", "농협손보"],
        "default_prod": "주력보종",
        "flyer": "농협손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "하나손보": {
        "category": "손해보험",
        "aliases": ["하나손해보험", "하나손보"],
        "default_prod": "주력보종",
        "flyer": "하나손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },

    # 생명보험사 (17개사)
    "흥국생명": {
        "category": "생명보험",
        "aliases": ["흥국생명", "흥국"],
        "default_prod": "오튼튼",
        "default_term": "20년납",
        "flyer": "흥국생명_11월.png",
        "recommendations": ["오튼튼 20만 20년납", "오튼튼 20만 10-11월 연속포함", "오튼튼 20만 핑크멤버스 포함", "다사랑 20만 20년납"]
    },
    "한화생명": {
        "category": "생명보험",
        "aliases": ["한화생명", "한화"],
        "default_prod": "건강더한종신",
        "default_term": "10년납",
        "flyer": "한화생명_11월.png",
        "recommendations": ["건강더한종신 50만 10년납", "건강더한종신 100만 10년납", "하나로H종신 50만 15년납"]
    },
    "DB생명": {
        "category": "생명보험",
        "aliases": ["DB생명", "디비생명", "동부생명", "DB", "디비"],
        "default_prod": "알행플종신",
        "default_term": "10년납",
        "flyer": "DB생명_11월.jpg",
        "recommendations": ["알행플종신 10만 10년납", "알행플종신 20만 10년납"]
    },
    "신한라이프": {
        "category": "생명보험",
        "aliases": ["신한라이프", "신한생명", "신한"],
        "default_prod": "신한통합건강 원",
        "default_term": "20년납",
        "flyer": "신한라이프_11월_p2.png",
        "recommendations": ["신한통합건강 원 20만", "신한통합건강 원 20만 연속포함", "모아더드림종신 20만"]
    },
    "KB라이프": {
        "category": "생명보험",
        "aliases": ["KB라이프", "KB생명", "케이비라이프", "케이비생명"],
        "default_prod": "딱좋은건강",
        "default_term": "20년납",
        "flyer": "KB라이프_11월.png",
        "recommendations": ["딱좋은건강 20만", "100세든든연금 20만"]
    },
    "라이나생명": {
        "category": "생명보험",
        "aliases": ["라이나생명", "라이나"],
        "default_prod": "새로담는건강보험",
        "default_term": "20년납",
        "flyer": "라이나생명_11월.png",
        "recommendations": ["새로담는건강 20만", "브레인케어 10만", "THE채우는종신 10년납 일반 20만", "THE채우는종신 7년납 20만"]
    },
    "미래에셋": {
        "category": "생명보험",
        "aliases": ["미래에셋생명", "미래에셋", "미래"],
        "default_prod": "M-케어건강",
        "default_term": "20년납",
        "flyer": "미래에셋_11월.png",
        "recommendations": ["M-케어건강 20만", "M-케어건강 10만", "M-케어건강 30만", "변액연금 20만"]
    },
    "메트라이프": {
        "category": "생명보험",
        "aliases": ["메트라이프", "메트"],
        "default_prod": "달러종신Plus",
        "default_term": "10년납",
        "flyer": "메트라이프_11월.jpg",
        "recommendations": ["달러종신Plus 20만 10년납", "달러종신Plus 20만 5년납", "달러종신Plus 20만 20년납", "변액리치 정기 20만"]
    },
    "동양생명": {
        "category": "생명보험",
        "aliases": ["동양생명", "동양"],
        "default_prod": "쑥쑥어린이",
        "default_term": "15년납",
        "flyer": "동양생명_11월.png",
        "recommendations": ["쑥쑥어린이 20만 15년납", "수호천사 20만"]
    },
    "교보생명": {
        "category": "생명보험",
        "aliases": ["교보생명", "교보"],
        "default_prod": "보장성",
        "default_term": "20년납",
        "flyer": "교보생명_11월.png",
        "recommendations": ["보장성 20만", "보장성 10만"]
    },
    "농협생명": {
        "category": "생명보험",
        "aliases": ["농협생명"],
        "default_prod": "건강플러스",
        "default_term": "20년납",
        "flyer": "농협생명_11월.png",
        "recommendations": ["건강플러스 20만", "투스텝종신 20만"]
    },
    "KDB생명": {
        "category": "생명보험",
        "aliases": ["KDB생명", "KDB"],
        "default_prod": "버팀목",
        "default_term": "10년납",
        "flyer": "KDB생명_11월.jpg",
        "recommendations": ["버팀목 20만", "버팀목 10만"]
    },
    "ABL생명": {
        "category": "생명보험",
        "aliases": ["ABL생명", "ABL"],
        "default_prod": "우리WON더채움",
        "default_term": "20년납",
        "flyer": "ABL생명_11월.png",
        "recommendations": ["우리WON더채움 20만", "우리WON세븐 20만"]
    },
    "하나생명": {
        "category": "생명보험",
        "aliases": ["하나생명"],
        "default_prod": "하나로라이트",
        "default_term": "20년납",
        "flyer": "하나생명_11월.png",
        "recommendations": ["하나로라이트 20만", "연결된종신 20만"]
    },
    "푸본현대": {
        "category": "생명보험",
        "aliases": ["푸본현대", "푸본"],
        "default_prod": "MAX원픽",
        "default_term": "20년납",
        "flyer": "푸본현대_11월.png",
        "recommendations": ["MAX원픽 20만", "마이픽 20만"]
    },
    "IM라이프": {
        "category": "생명보험",
        "aliases": ["IM라이프", "IM"],
        "default_prod": "당당한인생",
        "default_term": "7년납",
        "flyer": "IM라이프_11월.png",
        "recommendations": ["당당한인생 20만", "트래블PRO 20만"]
    },
    "IBK연금": {
        "category": "생명보험",
        "aliases": ["IBK연금", "IBK"],
        "default_prod": "프리미엄연금",
        "default_term": "10년납",
        "flyer": "IBK연금_11월.png",
        "recommendations": ["프리미엄연금 20만", "하이브리드연금 20만"]
    }
}


def clean_product_display_name(prod_name: str) -> str:
    cleaned = re.sub(r'\(.*?\)', '', prod_name)
    cleaned = re.sub(r'가입금액\s*[:：]?\s*.*', '', cleaned)
    cleaned = re.sub(r'[,\/].*', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else prod_name


def parse_premium(text: str) -> Optional[int]:
    """텍스트에서 보험료(원 단위)를 추출 (외화 가입금액 및 달러/불 제외)"""
    # 1. 외화 및 가입금액 마스킹
    cleaned = re.sub(r'\d+[\d,]*\s*만?\s*(?:달러|불|USD)', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'가입금액\s*[:：]?\s*\S+', '', cleaned)
    
    # 2. 'X만원' 또는 'X만 원' 우선 매칭
    m_won = re.search(r'(\d+[\d,]*)\s*만\s*원', cleaned)
    if m_won:
        return int(m_won.group(1).replace(',', '')) * 10000
        
    # 3. 'X만' 매칭 (뒤에 년/회/세/차/건/대/달러 등이 오지 않는 경우)
    m_man = re.search(r'(\d+[\d,]*)\s*만(?!\s*(?:년|회|세|차|건|대|달러|불|USD))', cleaned)
    if m_man:
        return int(m_man.group(1).replace(',', '')) * 10000
        
    # 4. 'X,000원' 또는 'X원'
    m2 = re.search(r'(\d+[\d,]{3,})\s*원', cleaned)
    if m2:
        return int(m2.group(1).replace(',', ''))
        
    # 5. 고립된 숫자
    m3 = re.search(r'\b(\d{1,4})\b', cleaned)
    if m3:
        val = int(m3.group(1))
        if val in [5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 70, 100, 150, 200, 300, 500]:
            return val * 10000
    return None


def find_companies_in_text(text: str) -> List[str]:
    """문장에서 언급된 보험사 목록을 정확하고 중복 없이 추출 (긴 별칭 우선)"""
    alias_map = []
    for comp, data in ALL_COMPANIES.items():
        for alias in data['aliases']:
            alias_map.append((alias, comp))
    alias_map.sort(key=lambda x: len(x[0]), reverse=True)
    
    found = []
    used_spans = []
    for alias, comp in alias_map:
        for m in re.finditer(re.escape(alias), text, re.IGNORECASE):
            span = m.span()
            if not any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                used_spans.append(span)
                if comp not in found:
                    found.append(comp)
    return found


def pick_best_term_product(candidates: List[Dict[str, Any]], term: str, default_term: str = "10년납") -> Dict[str, Any]:
    target_term = term if term else default_term
    m = re.search(r'(\d+)\s*년', target_term)
    target_years = m.group(1) if m else ""
    
    # 1. Regex boundary match: e.g. 5년 does not match 15년 or 25년
    if target_years:
        pattern = rf'(?<!\d){target_years}년'
        for p in candidates:
            if re.search(pattern, p.get('term', '')):
                return p
                
    for p in candidates:
        if default_term in p.get('term', ''):
            return p
    return candidates[0]


EN_KO_SYNONYMS = {
    'plus': '플러스',
    'one': '원',
    'max': '맥스',
    'pro': '프로',
    'ai': '에이아이',
    'gold': '골드',
    'classic': '클래식',
    'vip': '브이아이피',
    'gi': '지아이',
    'top': '탑',
    'pick': '픽',
    'h': '에이치',
    's': '에스',
    'w': '더블유',
    'new': '뉴',
    'up': '업',
    'free': '프리',
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = t.replace('(多)', '').replace('多', '').replace('(무)', '').replace('무배당', '')
    for en, ko in EN_KO_SYNONYMS.items():
        t = re.sub(rf'\b{en}\b|{en}', ko, t)
    t = t.replace('ⅲ', '3').replace('ⅱ', '2').replace('ⅰ', '1')
    t = t.replace('iii', '3').replace('ii', '2').replace('i', '1')
    return re.sub(r'[\s\(\)\[\]\{\}\-\_\,\.\:\/\+\#\*\~]', '', t)

GUBUN_KEYWORDS = [
    '간편가입', '간편심사형', '간편고지형', '간편가입형', '간편',
    '일반가입', '일반심사형', '일반가입형', '일반형', '일반',
    '체증형', '평준형', '체감형',
    '기본형', '기본납입형', '기본보장형', '기본',
    '해약환급금미지급형', '해지환급금미지급형', '해약환급금이없는유형', '미지급형', '미지급',
    '해약환급금일부지급형', '해지환급금일부지급형', '일부지급형',
    '표준형', '상생협력형',
    '라이프밸런스형', '라이프밸런스', '프리미엄보장형',
    '종합설계형', '3대질환보장형', '3대질환',
    '보증형', '미보증형', '계약자적립액보증형', '계약자적립액미보증형',
    '비갱신형', '비갱신', '갱신형', '갱신',
    '300천이상', '250천이상', '200천이상', '150천이상', '100천이상',
    '250달러이상', '200달러이상', '150달러이상', '100달러이상',
    '3천만이상', '2천만이상', '1억이상'
]

GUBUN_SYNONYMS = {
    '비갱신형': ['해약환급금 미지급형', '해지환급금 미지급형', '해약환급금이없는유형', '미지급형', '표준형'],
    '비갱신': ['해약환급금 미지급형', '해지환급금 미지급형', '해약환급금이없는유형', '미지급형', '표준형'],
    '미지급형': ['해약환급금 미지급형', '해지환급금 미지급형'],
    '미지급': ['해약환급금 미지급형', '해지환급금 미지급형'],
    '갱신형': ['갱신형', '갱신'],
    '갱신': ['갱신형'],
    '일반': ['일반가입', '일반심사형', '일반가입형', '일반형'],
    '간편': ['간편가입', '간편심사형', '간편고지형', '간편가입형'],
    '기본': ['기본형', '기본납입형', '기본보장형'],
    '체증': ['체증형', '1형 (5%체증형)', '2형 (10%체증형)']
}

REGULATORY_PATTERNS = [
    r'\(무\)',
    r'무배당',
    r'\(해약환급금\s*미지급형\)',
    r'\(해지환급금\s*미지급형\)',
    r'\(해약환급금\s*일부지급형\)',
    r'\(해지환급금\s*일부지급형\)',
    r'\(해약환급금일부지급형[ⅠⅡⅢ]*\)',
    r'\(해지환급금일부지급형[ⅠⅡⅢ]*\)',
    r'\(해약환급금\s*일부\(50%\)지급형\)',
    r'\(보증비용부과형\)',
    r'\(해지환급금보증형\)',
    r'\(주계약기준\)',
    r'\(주계약\)',
    r'가입금액:.*',
    r'보종코드:.*',
]

def clean_prod_short_name(prod: str) -> str:
    p = prod
    for pat in REGULATORY_PATTERNS:
        p = re.sub(pat, '', p)
    p = re.sub(r'\s+', ' ', p).strip()
    return p if len(p) >= 2 else prod

LIFE_CATALOG: Dict[Tuple[str, str], Dict[str, Any]] = {}
for d in LIFE_PRODUCTS:
    d['company'] = d.get('company', '').replace('\n', '').strip()
    sheet = d.get('sheet', '').strip()
    prod = d.get('product', '').strip()
    key = (sheet, prod)
    if key not in LIFE_CATALOG:
        has_ganpyeon_in_name = any(k in prod for k in ['(간편)', '(간편한)', '간편가입', '간편심사'])
        clean_p = clean_prod_short_name(prod)
        search_keys = set()
        norm_p = normalize_text(prod)
        search_keys.add(norm_p)
        search_keys.add(normalize_text(clean_p))

        # 회사명 접두어 제거 버전
        no_comp = re.sub(r'^(교보|한화|동양|신한|흥국|db|kb|kdb|abl|하나|푸본|im|ibk|라이나|메트|농협|미래)\s*', '', prod, flags=re.IGNORECASE)
        search_keys.add(normalize_text(no_comp))
        search_keys.add(normalize_text(clean_prod_short_name(no_comp)))

        # (간편) 포함 상품인 경우: 간편 제거 및 일반 버전 추가 (일반/간편 동일 환산·시책)
        if has_ganpyeon_in_name:
            no_ganpyeon = re.sub(r'\(간편한?\)|간편한?가입?심사?', '', prod)
            search_keys.add(normalize_text(no_ganpyeon))
            search_keys.add(normalize_text(clean_prod_short_name(no_ganpyeon)))

            no_comp_no_g = re.sub(r'^(교보|한화|동양|신한|흥국|db|kb|kdb|abl|하나|푸본|im|ibk|라이나|메트|농협|미래)\s*', '', no_ganpyeon, flags=re.IGNORECASE)
            search_keys.add(normalize_text(no_comp_no_g))
            search_keys.add(normalize_text(clean_prod_short_name(no_comp_no_g)))

            ilban_ver = re.sub(r'\(간편한?\)|간편한?가입?심사?', '일반', prod)
            search_keys.add(normalize_text(ilban_ver))
            search_keys.add(normalize_text(clean_prod_short_name(ilban_ver)))

        if '3밸런스' in prod:
            search_keys.update(['3밸런스', '3밸런스보장보험', '3밸런스보장보험플러스', '3밸런스플러스', '3밸런스plus'])
        if '밸런스건강' in prod:
            search_keys.update(['밸런스건강', '밸런스건강보험'])
        if '드림종신' in prod:
            search_keys.update(['우리won드림종신', '우리won드림종신3', 'won드림종신', '드림종신', '드림종신3'])

        LIFE_CATALOG[key] = {
            'sheet': sheet,
            'company': d.get('company', '').strip(),
            'full_product': prod,
            'norm_name': norm_p,
            'clean_norm': normalize_text(clean_p),
            'search_keys': {k for k in search_keys if k},
            'has_ganpyeon_merged': has_ganpyeon_in_name,
            'gubuns': [],
            'terms': [],
            'items': []
        }
    g = d.get('gubun', '').strip()
    t = d.get('term', '').strip()
    # 납기형 표기(10년납, 20년납 이상)나 일반,간편 병합 표기는 별도 선택지 질문에서 제외
    if g and not re.search(r'^\d+\s*년', g):
        if g not in ['-', '일반,간편', '일반심사 간편심사']:
            if g not in LIFE_CATALOG[key]['gubuns']:
                LIFE_CATALOG[key]['gubuns'].append(g)
    if t and t not in LIFE_CATALOG[key]['terms']:
        LIFE_CATALOG[key]['terms'].append(t)
    LIFE_CATALOG[key]['items'].append(d)


def extract_gubun_from_query(query: str) -> Optional[str]:
    q_norm = normalize_text(query)
    for g in sorted(GUBUN_KEYWORDS, key=len, reverse=True):
        if normalize_text(g) in q_norm:
            return g
    return None

def find_candidate_products(company: str, utterance: str) -> List[Dict[str, Any]]:
    comp_clean = company.replace('생명', '').replace('라이프', '').replace('화재', '').replace('손보', '').replace('연금', '').strip().lower()
    if comp_clean in ['kb', '케이비']: comp_clean = 'KB'
    elif comp_clean in ['디비', 'db']: comp_clean = 'DB'
    elif comp_clean in ['아이엠', 'im']: comp_clean = 'IM'
    elif comp_clean in ['미래', '미래에셋']: comp_clean = '미래'
    elif comp_clean in ['ibk', '기업']: comp_clean = 'IBK'

    sheet_prods = [
        p for (s, _), p in LIFE_CATALOG.items()
        if s.lower() == comp_clean.lower() or s.lower() in comp_clean.lower() or comp_clean.lower() in s.lower() or comp_clean.lower() in p['company'].lower()
    ]
    if not sheet_prods:
        return []

    # 1. 원본 쿼리 정제 (회사명, 납기, 금액, 계산어만 제거)
    cleaned_raw = utterance
    for comp_token in [comp_clean, '생명', '라이프', '화재', '손보']:
        cleaned_raw = re.sub(rf'\b{comp_token}\b|{comp_token}', ' ', cleaned_raw, flags=re.IGNORECASE)
    cleaned_raw = re.sub(r'(\d+)\s*년\s*납?|전기납', ' ', cleaned_raw)
    cleaned_raw = re.sub(r'(\d+[\d,]*)\s*(?:만원|만|원)', ' ', cleaned_raw)
    cleaned_raw = re.sub(r'계산|시책|얼마|수수료|알려줘|비교|안내|문의|설계|상품', ' ', cleaned_raw)
    cleaned_raw = re.sub(r'\b\d{5,}\b', ' ', cleaned_raw)  # 금액 성격의 5자리 이상 숫자만 제거

    q_norm_raw = normalize_text(cleaned_raw)

    # [0단계 우선 검증] 원본 정제 텍스트 그대로 정확히 일치하는 단일 상품이 있으면 즉시 반환 (루프 방지)
    if q_norm_raw:
        exact_raw = [p for p in sheet_prods if p['norm_name'] == q_norm_raw or q_norm_raw in p.get('search_keys', set())]
        if len(exact_raw) == 1:
            return exact_raw

    # 2. 구분(종: 일반/간편/기본/체증형/비갱신/갱신/미지급 등) 키워드 분리
    detected_gubun = extract_gubun_from_query(utterance)
    q_norm = q_norm_raw
    if detected_gubun:
        d_norm = normalize_text(detected_gubun)
        if d_norm and d_norm in q_norm:
            q_norm = q_norm.replace(d_norm, '')
        if detected_gubun in ['비갱신형', '비갱신']:
            for syn in ['비갱신형', '비갱신', '해약환급금미지급형', '해지환급금미지급형', '해약환급금이없는유형', '미지급형', '미지급']:
                q_norm = q_norm.replace(syn, '')
        elif detected_gubun in ['갱신형', '갱신']:
            q_norm = q_norm.replace('갱신형', '').replace('갱신', '')

    if not q_norm:
        return sheet_prods[:6]

    # [3단계] 원본 발화(공백·특수문자만 제거) 내에 상품명 전체가 포함되어 있는 경우 (최우선 부분문자열 일치)
    raw_norm = normalize_text(utterance)
    # 회사명 제거한 순수 상품명 검색
    contained_in_raw = [
        p for p in sheet_prods
        if (p['norm_name'] in raw_norm or p['clean_norm'] in raw_norm or any(k in raw_norm for k in p.get('search_keys', set())))
        and len(p['clean_norm']) >= 3
    ]
    if len(contained_in_raw) == 1:
        return contained_in_raw
    elif len(contained_in_raw) > 1:
        max_l = max(len(p['clean_norm']) for p in contained_in_raw)
        longest = [p for p in contained_in_raw if len(p['clean_norm']) == max_l]
        if len(longest) == 1:
            return longest
        if detected_gubun:
            d_norm = normalize_text(detected_gubun)
            g_filter = [c for c in longest if d_norm in c['norm_name'] or any(d_norm in normalize_text(g) for g in c.get('gubuns', []))]
            if len(g_filter) == 1:
                return g_filter
        return longest[:6]

    # [4단계] 구분 제거 후 정규화 텍스트 완전 일치 (원본 norm 또는 clean_norm 또는 search_keys)
    exact_matches = [p for p in sheet_prods if p['norm_name'] == q_norm or p.get('clean_norm') == q_norm or q_norm in p.get('search_keys', set())]
    if len(exact_matches) == 1:
        return exact_matches
    elif len(exact_matches) > 1:
        if detected_gubun:
            d_norm = normalize_text(detected_gubun)
            g_filter = [c for c in exact_matches if d_norm in c['norm_name'] or any(d_norm in normalize_text(g) for g in c.get('gubuns', [])) or (c.get('has_ganpyeon_merged') and d_norm in ['일반', '간편'])]
            if len(g_filter) == 1:
                return g_filter
            elif len(g_filter) > 1:
                return g_filter
        return exact_matches

    # [5단계] 쿼리가 상품명을 포함하는 경우
    contains_matches = [p for p in sheet_prods if (p['norm_name'] in q_norm and len(p['norm_name']) >= 2) or any(k in q_norm and len(k) >= 2 for k in p.get('search_keys', set()))]
    if len(contains_matches) == 1:
        return contains_matches
    elif len(contains_matches) > 1:
        max_len = max(len(p['norm_name']) for p in contains_matches)
        longest = [p for p in contains_matches if len(p['norm_name']) == max_len]
        if len(longest) == 1:
            return longest
        if detected_gubun:
            d_norm = normalize_text(detected_gubun)
            g_filter = [c for c in longest if d_norm in c['norm_name'] or any(d_norm in normalize_text(g) for g in c.get('gubuns', [])) or (c.get('has_ganpyeon_merged') and d_norm in ['일반', '간편'])]
            if len(g_filter) == 1:
                return g_filter
        return longest[:6]

    # [6단계] 상품명이 쿼리를 포함하는 경우 (사용자가 단축 상품명 입력)
    sub_matches = [p for p in sheet_prods if (q_norm in p['norm_name'] and len(q_norm) >= 2) or any(q_norm in k and len(q_norm) >= 2 for k in p.get('search_keys', set()))]
    if len(sub_matches) == 1:
        return sub_matches
    elif len(sub_matches) > 1:
        if detected_gubun:
            d_norm = normalize_text(detected_gubun)
            g_filter = [c for c in sub_matches if d_norm in c['norm_name'] or any(d_norm in normalize_text(g) for g in c.get('gubuns', [])) or (c.get('has_ganpyeon_merged') and d_norm in ['일반', '간편'])]
            if len(g_filter) == 1:
                return g_filter
            elif len(g_filter) > 1:
                return g_filter[:6]
        return sub_matches[:6]

    # [7단계] 숫자 버전 패턴 매칭 (3.10.5, 5.10.5 등 특수 버전코드만)
    q_vers = [v for v in re.findall(r'\d+n\d+|\d+', q_norm) if len(v) >= 3 and v not in ['100', '10', '15', '20', '30']]
    if q_vers:
        num_matches = []
        for p in sheet_prods:
            p_vers = [v for v in re.findall(r'\d+n\d+|\d+', p['norm_name']) if len(v) >= 3 and v not in ['100', '10', '15', '20', '30']]
            if any(v in p_vers for v in q_vers):
                num_matches.append(p)
        if len(num_matches) == 1:
            return num_matches
        elif len(num_matches) > 1:
            if detected_gubun:
                d_norm = normalize_text(detected_gubun)
                g_filter = [c for c in num_matches if d_norm in c['norm_name'] or any(d_norm in normalize_text(g) for g in c.get('gubuns', []))]
                if len(g_filter) == 1:
                    return g_filter
            return num_matches[:6]

    # [8단계] 2-gram 유사도 매칭 (최후의 수단)
    fuzzy_matches = []
    for p in sheet_prods:
        pn = p['norm_name']
        matches = sum(1 for i in range(len(q_norm)-1) if q_norm[i:i+2] in pn)
        if matches >= 2:
            fuzzy_matches.append((matches, p))
    if fuzzy_matches:
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        top_score = fuzzy_matches[0][0]
        top_fuzzies = [p for s, p in fuzzy_matches if s == top_score]
        if len(top_fuzzies) == 1:
            return top_fuzzies
        return top_fuzzies[:6]

    return []

def match_gubun_in_text(prod_group: Optional[Dict[str, Any]], utterance: str) -> Optional[str]:
    if not prod_group:
        return ""
    gubuns = prod_group.get('gubuns', [])
    if not gubuns:
        return ""
    if len(gubuns) == 1:
        return gubuns[0]

    u_norm = normalize_text(utterance)
    # 1. 직접 포함 검사
    for g in gubuns:
        g_norm = normalize_text(g)
        if g_norm in u_norm:
            return g

    detected = extract_gubun_from_query(utterance)
    if detected:
        d_norm = normalize_text(detected)
        for g in gubuns:
            if d_norm in normalize_text(g) or normalize_text(g) in d_norm:
                return g
        syns = GUBUN_SYNONYMS.get(detected, [])
        for syn in syns:
            s_norm = normalize_text(syn)
            for g in gubuns:
                if s_norm in normalize_text(g) or normalize_text(g) in s_norm:
                    return g

    # 비갱신 vs 갱신형 전용 매핑
    if any(k in u_norm for k in ['비갱신', '미지급', '무해지']):
        for g in gubuns:
            if any(k in normalize_text(g) for k in ['미지급', '표준형', '비갱신']):
                return g
    if any(k in u_norm for k in ['갱신', '갱신형']):
        for g in gubuns:
            if '갱신' in normalize_text(g):
                return g

    return None

def parse_term_to_years(t_str: str) -> Optional[int]:
    m = re.search(r'(\d+)\s*년', t_str)
    return int(m.group(1)) if m else None

def resolve_term_against_valid_terms(user_term_str: str, valid_terms: List[str]) -> Optional[str]:
    if not valid_terms:
        return user_term_str

    u_clean = user_term_str.replace(' ', '')

    # 1. 완전 텍스트 일치 또는 포함
    for t in valid_terms:
        t_clean = t.replace(' ', '')
        if u_clean == t_clean or u_clean in t_clean or t_clean in u_clean:
            # 사용자가 '10년'처럼 명시했는데 '10년미만', '10년이하'에 오매칭되는 것 방지
            if ('미만' in t or '이하' in t) and not ('미만' in user_term_str or '이하' in user_term_str):
                continue
            return t

    # 2. 숫자(년수) 기반 정밀 매칭
    req_y = parse_term_to_years(user_term_str)
    if req_y is None:
        for t in valid_terms:
            if '전기' in user_term_str and '전기' in t:
                return t
        return None

    # 2-A: 단일 연도 완전 일치 우선 (범위/이상/미만 제외한 순수 연도)
    for t in valid_terms:
        if not any(k in t for k in ['~', '–', '-', '이상', '미만', '이하', '↑', '만기', '세', '/']):
            y = parse_term_to_years(t)
            if y == req_y:
                return t

    # 2-B: 구간/범위 매칭 (예: 5~6년, 7~9년, 10~14년, 10-14년, 15-19년)
    for t in valid_terms:
        m_range = re.search(r'(\d+)\s*[\~–\-]\s*(\d+)\s*년', t)
        if m_range:
            start_y, end_y = int(m_range.group(1)), int(m_range.group(2))
            if start_y <= req_y <= end_y:
                return t

    # 2-C: N년이상 매칭 (예: 10년이상, 15년이상, 20년이상)
    ge_candidates = []
    for t in valid_terms:
        if any(k in t for k in ['이상', '↑']):
            y = parse_term_to_years(t)
            if y is not None and req_y >= y:
                ge_candidates.append((y, t))
    if ge_candidates:
        ge_candidates.sort(key=lambda x: x[0], reverse=True)
        return ge_candidates[0][1]

    # 2-D: N년미만 / 이하 매칭 (예: 10년미만, 9년납이하)
    le_candidates = []
    for t in valid_terms:
        if '미만' in t:
            y = parse_term_to_years(t)
            if y is not None and req_y < y:
                le_candidates.append((y, t))
        elif '이하' in t:
            y = parse_term_to_years(t)
            if y is not None and req_y <= y:
                le_candidates.append((y, t))
    if le_candidates:
        le_candidates.sort(key=lambda x: x[0])
        return le_candidates[0][1]

    # 2-E: 슬래시/쉼표 복합 매칭 (예: 10,11년납, 10년/12년, 15년/20년납)
    for t in valid_terms:
        nums = [int(n) for n in re.findall(r'\d+', t)]
        if req_y in nums:
            return t

    return None

def extract_requested_term_from_utterance(utterance: str, prod_group: Optional[Dict[str, Any]] = None) -> Optional[str]:
    u = utterance
    if prod_group:
        p_clean = clean_prod_short_name(prod_group.get('full_product', ''))
        u = u.replace(p_clean, ' ')
        for k in prod_group.get('search_keys', set()):
            if len(k) >= 3:
                u = u.replace(k, ' ')

    m = re.search(r'(\d+)\s*년\s*(?:납\s*)?(?:이상|미만|이하|만기)?|전기납|(\d+)\s*세\s*납', u)
    if m:
        return m.group(0).replace(" ", "")
    return None

def match_term_in_text(prod_group: Optional[Dict[str, Any]], utterance: str) -> Tuple[Optional[str], Optional[str]]:
    """
    반환: (matched_term, invalid_requested_term)
    - matched_term: 유효한 조견표 납기 (계산 가능)
    - invalid_requested_term: 사용자가 명시했으나 조견표에 존재하지 않는 납기 (예: 7년납 없음)
    - 둘 다 None: 사용자가 납기를 입력하지 않음
    """
    if not prod_group:
        return None, None
    valid_terms = prod_group.get('terms', [])
    if not valid_terms:
        return "20년납", None

    u_clean = utterance.replace(" ", "")

    # 1. 발화 내에 유효 납기가 직접 포함되어 있는지 검사 (예: 1형 (5%체증형), 해약환급금일부지급형, 90세납, 10년만기 등)
    for t in valid_terms:
        if t and t != '-' and t.replace(" ", "") in u_clean:
            # 단, '10년'이 '10년미만'에 부분일치되는 오인식 방지
            if ('미만' in t or '이하' in t) and not ('미만' in utterance or '이하' in utterance):
                continue
            return t, None

    # 2. 사용자가 발화한 납기 문자열 추출
    req_term = extract_requested_term_from_utterance(utterance, prod_group)

    if req_term:
        resolved = resolve_term_against_valid_terms(req_term, valid_terms)
        if resolved:
            return resolved, None
        else:
            return None, req_term

    # 3. 사용자가 납기를 명시하지 않은 경우
    if len(valid_terms) == 1:
        return valid_terms[0], None
    if valid_terms == ['-'] or valid_terms == ['']:
        return '-', None

    return None, None

def match_master_item(prod_group: Dict[str, Any], term: str, gubun: str) -> Dict[str, Any]:
    items = prod_group.get('items', [])
    if not items:
        return {'s_factor': 1000.0, 'adj_coef': 1.0, 'raw_factor': 1000.0}
    if gubun:
        matched = [it for it in items if it['term'] == term and it['gubun'] == gubun]
        if matched: return matched[0]
        matched = [it for it in items if it['term'] == term and (gubun in it['gubun'] or it['gubun'] in gubun)]
        if matched: return matched[0]

    matched = [it for it in items if it['term'] == term or term in it['term']]
    if matched: return matched[0]
    return items[0]

def search_life_product(company: str, query: str, term: str = "") -> Optional[Dict[str, Any]]:
    candidates = find_candidate_products(company, query)
    if not candidates:
        return None
    prod_group = candidates[0]
    gubun = match_gubun_in_text(prod_group, query)
    item = match_master_item(prod_group, term or (prod_group['terms'][0] if prod_group['terms'] else "10년납"), gubun or "")
    return item

def get_sky_jongshin_bonus(comp: str, prod: str, term: str, premium: int, is_corp: bool = False) -> Tuple[int, str]:
    """스카이블루에셋 11월 본사 종신전략상품 추가지원안 (구간별 고정 시상금액, 익월 50% + 15회차 50%)"""
    c = comp.lower()
    p = prod.lower()
    t = term.lower()
    
    # 1. DB알행종 (10년납, 7년납) - 개인/법인 모두 지급
    if ('db' in c or '디비' in c) and any(k in p for k in ['알행종', '알행플', '알차고']):
        if '10년' in t:
            if premium >= 24000000: return 60000000, "DB알행종 10년납 SKY본사추가 6,000만원(익월3000+15회3000)"
            elif premium >= 18000000: return 45000000, "DB알행종 10년납 SKY본사추가 4,500만원(익월2250+15회2250)"
            elif premium >= 12000000: return 30000000, "DB알행종 10년납 SKY본사추가 3,000만원(익월1500+15회1500)"
            elif premium >= 8400000: return 21000000, "DB알행종 10년납 SKY본사추가 2,100만원(익월1050+15회1050)"
            elif premium >= 6000000: return 15000000, "DB알행종 10년납 SKY본사추가 1,500만원(익월750+15회750)"
            elif premium >= 3600000: return 9000000, "DB알행종 10년납 SKY본사추가 900만원(익월450+15회450)"
            elif premium >= 2400000: return 6000000, "DB알행종 10년납 SKY본사추가 600만원(익월300+15회300)"
            elif premium >= 1200000: return 3000000, "DB알행종 10년납 SKY본사추가 300만원(익월150+15회150)"
        elif '7년' in t:
            if premium >= 24000000: return 40000000, "DB알행종 7년납 SKY본사추가 4,000만원(익월2000+15회2000)"
            elif premium >= 18000000: return 30000000, "DB알행종 7년납 SKY본사추가 3,000만원(익월1500+15회1500)"
            elif premium >= 12000000: return 20000000, "DB알행종 7년납 SKY본사추가 2,000만원(익월1000+15회1000)"
            elif premium >= 8400000: return 15000000, "DB알행종 7년납 SKY본사추가 1,500만원(익월750+15회750)"
            elif premium >= 6000000: return 10000000, "DB알행종 7년납 SKY본사추가 1,000만원(익월500+15회500)"
            elif premium >= 3600000: return 6000000, "DB알행종 7년납 SKY본사추가 600만원(익월300+15회300)"
            elif premium >= 2400000: return 4000000, "DB알행종 7년납 SKY본사추가 400만원(익월200+15회200)"
            elif premium >= 1200000: return 2000000, "DB알행종 7년납 SKY본사추가 200만원(익월100+15회100)"

    # 2. 한화생명 하나로 (15년납·법인계약만)
    elif ('한화' in c) and ('하나로' in p):
        if is_corp and ('15년' in t or '20년' in t):
            if premium >= 24000000: return 60000000, "한화하나로 15년납 SKY법인추가 6,000만원(익월3000+15회3000)"
            elif premium >= 18000000: return 45000000, "한화하나로 15년납 SKY법인추가 4,500만원(익월2250+15회2250)"
            elif premium >= 12000000: return 30000000, "한화하나로 15년납 SKY법인추가 3,000만원(익월1500+15회1500)"
            elif premium >= 8400000: return 21000000, "한화하나로 15년납 SKY법인추가 2,100만원(익월1050+15회1050)"
            elif premium >= 6000000: return 15000000, "한화하나로 15년납 SKY법인추가 1,500만원(익월750+15회750)"
            elif premium >= 3600000: return 9000000, "한화하나로 15년납 SKY법인추가 900만원(익월450+15회450)"
            elif premium >= 2400000: return 2400000, "한화하나로 15년납 SKY법인추가 240만원(익월120+15회120)"
            elif premium >= 1200000: return 1200000, "한화하나로 15년납 SKY법인추가 120만원(익월60+15회60)"

    # 3. 푸본현대 맥스원픽 / IM당당한인생 (7년납·법인계약만)
    elif (('푸본' in c and '원픽' in p) or ('im' in c and '당당한' in p)):
        if is_corp and '7년' in t:
            label = "푸본맥스원픽" if '푸본' in c else "IM당당한인생"
            if premium >= 24000000: return 40000000, f"{label} 7년납 SKY법인추가 4,000만원(익월2000+15회2000)"
            elif premium >= 18000000: return 30000000, f"{label} 7년납 SKY법인추가 3,000만원(익월1500+15회1500)"
            elif premium >= 12000000: return 20000000, f"{label} 7년납 SKY법인추가 2,000만원(익월1000+15회1000)"
            elif premium >= 8400000: return 15000000, f"{label} 7년납 SKY법인추가 1,500만원(익월750+15회750)"
            elif premium >= 6000000: return 10000000, f"{label} 7년납 SKY법인추가 1,000만원(익월500+15회500)"
            elif premium >= 3600000: return 6000000, f"{label} 7년납 SKY법인추가 600만원(익월300+15회300)"
            elif premium >= 2400000: return 2400000, f"{label} 7년납 SKY법인추가 240만원(익월120+15회120)"
            elif premium >= 1200000: return 1200000, f"{label} 7년납 SKY법인추가 120만원(익월60+15회60)"

    return 0, ""


def get_sky_health_bonus(comp: str, prod: str, premium: int) -> Tuple[float, str]:
    """스카이블루에셋 11월 본사 건강전략상품 추가시상안 (P 10만↑ 100%, P 20만↑ 200% 익월지급)"""
    c = comp.lower()
    p = prod.lower()
    
    # 1. DB건강 4종: {생활비암, 내가고른, 건강100, 치매간병}
    if ('db' in c or '디비' in c) and any(k in p for k in ['생활비암', '내가고른', '건강100', '치매간병', '치매', '간병', '7대질병', '올케어', '건강', '통합']):
        if premium >= 200000: return 2.0, "SKY본사 건강추가 200%(익월)"
        elif premium >= 100000: return 1.0, "SKY본사 건강추가 100%(익월)"
            
    # 2. 흥국건강 5종: {오튼튼, 3.10.5, 고당+, 3.8.5.5, 다사랑3N5, 치매담은(시니어, PLUS)}
    elif '흥국' in c and any(k in p for k in ['오튼튼', '3.10.5', '고당', '3.8.5.5', '3n5', '다사랑', '치매담은', '시니어', '건강', '암']):
        if premium >= 200000: return 2.0, "SKY본사200"
        elif premium >= 100000: return 1.0, "SKY본사100"
            
    return 0.0, ""

def get_life_incentive(comp_name: str, product_name: str, term: str = "", premium: int = 200000, incentive_type: str = "전략", continuous_mode: str = "none", contract_type: str = "개인", gubun: str = "") -> Dict[str, Any]:
    """17개 생보사 11월 공식 시책표 정밀 판정 (메트라이프 납기별 차이, 흥국 2종 연속, 신한 3~7번 연계, 라이나, 미래에셋 완벽 반영)"""
    comp = comp_name.replace('생명', '').replace('라이프', '').strip().lower()
    prod = product_name.replace(" ", "").lower()
    
    # 1. 메트라이프생명 (사용자 지시: 납입기간에 따라 s환산차이 크고 시책도 상이)
    if '메트' in comp:
        if '달러' in prod or '백만인' in prod or '종신' in prod:
            m_y = re.search(r'(\d+)\s*년', term)
            years = int(m_y.group(1)) if m_y else 10
            if years <= 5:
                return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (달러종신Plus 5년납 250%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif years in [7, 10]:
                return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": f"익월 400% (달러종신Plus {years}년납 400%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '3년내고' in prod or years == 3:
                return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (3년내고 만족하는 달러종신 250%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": f"익월 400% (달러종신Plus {years}년납 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '정기' in prod or '변액리치' in prod:
            return {"next_month": 2.0, "split": 2.5, "total": 4.5, "basis": "익월 200% + 15차월 250% (변액리치 정기 450%)", "cont_bonus": 0.3, "cont_desc": "전략상품 1건 이상 가동 시 15차월 추가 +30%"}
        elif '연금' in prod:
            return {"next_month": 3.0, "split": 0.0, "total": 3.0, "basis": "익월 300% (오로지연금을위한 달러연금 300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '무해약' in prod or '해약' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (간편 360 종합 무해약환급형 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '암' in prod:
            return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (360 암보험 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '간편' in prod or '종합' in prod or '360' in prod:
            return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (간편 360 종합 갱신형 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (메트라이프 전략 250%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 2. 흥국생명 (10~11월 연속가동 & 핑크멤버스 2종 연속시상)
    elif '흥국' in comp:
        is_strat = (incentive_type == "전략" or any(k in prod for k in ['오튼튼', '다사랑', '치매', '암', '건강', '3.10.5']))
        base_next = 4.0
        sky_next = 0.0
        sky_health_desc = ""
        if is_strat:
            if premium >= 200000:
                sky_next = 2.0
                sky_health_desc = "SKY본사200"
            elif premium >= 100000:
                sky_next = 1.0
                sky_health_desc = "SKY본사100"
        install_period = 6.0
        install_strat = 2.0 if is_strat else 0.0
        
        c1_amount = 0
        if premium >= 1000000: c1_amount = 10000000
        elif premium >= 700000: c1_amount = 7000000
        elif premium >= 500000: c1_amount = 5000000
        elif premium >= 300000: c1_amount = 1800000
        elif premium >= 200000: c1_amount = 1200000
        elif premium >= 100000: c1_amount = 600000
        elif premium >= 50000: c1_amount = 300000
        
        c2_amount = 0
        if premium >= 1000000: c2_amount = 5000000
        elif premium >= 700000: c2_amount = 3500000
        elif premium >= 500000: c2_amount = 2500000
        elif premium >= 300000: c2_amount = 1500000
        elif premium >= 200000: c2_amount = 1000000
        elif premium >= 100000: c2_amount = 500000

        c1_rate = (c1_amount / premium) if premium > 0 else 0.0
        c2_rate = (c2_amount / premium) if premium > 0 else 0.0

        applied_cont_rate = 0.0
        applied_desc = ""
        c_mode = continuous_mode.lower()
        if "c1" in c_mode or "10-11" in c_mode or "10월연속" in c_mode or "연속가동" in c_mode:
            applied_cont_rate = c1_rate
            applied_desc = f"[10~11월 연속가동 +{c1_amount//10000}만 원({int(c1_rate*100)}%) 합산]"
        elif "c2" in c_mode or "핑크" in c_mode:
            applied_cont_rate = c2_rate
            applied_desc = f"[핑크멤버스 +{c2_amount//10000}만 원({int(c2_rate*100)}%) 합산]"
        elif "both" in c_mode or "all" in c_mode or "full" in c_mode or "풀" in c_mode or "모두" in c_mode or "둘다" in c_mode or "연속포함" in c_mode or c_mode == "true":
            applied_cont_rate = c1_rate + c2_rate
            applied_desc = f"[연속 2종 모두포함 +{(c1_amount+c2_amount)//10000}만 원({int((c1_rate+c2_rate)*100)}%) 합산]"

        basis = f"익월 {int((base_next+sky_next)*100)}%(원수사400+{sky_health_desc}) + 13회차 {int((install_period+install_strat)*100)}%(1~3주600+전략{int(install_strat*100)})"
        if applied_desc:
            basis += f" {applied_desc}"

        return {
            "next_month": base_next + sky_next,
            "split": install_period + install_strat + applied_cont_rate,
            "total": base_next + sky_next + install_period + install_strat + applied_cont_rate,
            "basis": basis,
            "c1_amount": c1_amount,
            "c2_amount": c2_amount,
            "cont_bonus": c1_rate + c2_rate,
            "cont_desc": f"① 10~11월 연속가동(+{c1_amount//10000}만) ② 핑크멤버스(+{c2_amount//10000}만)",
            "is_heungkuk": True,
            "continuous_mode": continuous_mode
        }

    # 3. 한화생명
    elif '한화' in comp:
        if '건강더한' in prod:
            if '7년' in term:
                return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (건강더한종신 7년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (건강더한종신 10년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '하나로' in prod:
            base_next = 3.5 if '10년' in term else 5.0
            base_split = 1.5 if '10년' in term else 2.0
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("한화생명", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            tot_rate = tot_next + tot_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and ('15년' in term or '20년' in term):
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif '필요할때' in prod:
            if '12년' in term:
                return {"next_month": 6.0, "split": 2.5, "total": 8.5, "basis": "익월 600% + 13회차 250% (필요할때쓰는종신 12년납 850%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.5, "split": 2.0, "total": 6.5, "basis": "익월 450% + 13회차 200% (필요할때쓰는종신 10년납 650%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '밸류플러스' in prod:
            return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (밸류플러스2.0 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '치매' in prod or '간병' in prod:
            return {"next_month": 5.0, "split": 3.0, "total": 8.0, "basis": "익월 500% + 13회차 300% (치매담은 간병플러스 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '암' in prod or '시그니처' in prod:
            return {"next_month": 5.0, "split": 8.0, "total": 13.0, "basis": "익월 500% + 13회차 800% (시그니처암 1,300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif 'h종신' in prod or 'h' in prod:
            return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (H종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (한화생명 주력 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 4. DB생명
    elif ('kdb' not in comp) and ('db' in comp or '디비' in comp or '동부' in comp):
        if any(k in prod for k in ['알행플', '알행종', '알차고']):
            base_next = 4.0
            base_split = 1.0 if '7년' in term else 2.0
            sky_amount, sky_desc = get_sky_jongshin_bonus("DB생명", prod, term, premium, is_corp=True)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            tot_rate = tot_next + tot_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            return {"next_month": tot_next, "split": tot_split, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['생활비암', '내가고른', '건강100', '치매간병', '치매', '간병', '7대질병', '올케어', '건강', '통합']):
            base_next = 4.0
            base_split = 2.0
            sky_rate, sky_desc = get_sky_health_bonus("DB생명", prod, premium)
            tot_next = base_next + sky_rate
            tot_split = base_split
            basis = f"원수사 600%(익월400+13회200)"
            if sky_desc:
                basis += f" + {sky_desc}"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif '리턴' in prod:
            return {"next_month": 4.0, "split": 2.0, "total": 6.0, "basis": "원수사 600% (익월 400% + 13회차 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '올케어' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "원수사 800% (익월 400% + 13회차 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 4.0, "split": 2.0, "total": 6.0, "basis": "원수사 600% (익월 400% + 13회차 200%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 5. 신한라이프 (2번째장 3~7번 연계는 연속포함 시에만 합산)
    elif '신한' in comp:
        if '모아더드림plus' in prod or '모아더드림플러스' in prod:
            return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (모아더드림Plus 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '모아더드림' in prod or '리필' in prod or '3케어' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (모아더드림/리필종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '든든한' in prod or 'the든든한' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (THE든든한종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '변액' in prod:
            return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (ONE더드림 변액연금 강화형 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '연금' in prod:
            return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (ONE더라이프 연금 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            next_m = 2.5
            base_split_amount = 0
            if premium >= 600000: base_split_amount = 7200000
            elif premium >= 400000: base_split_amount = 4800000
            elif premium >= 250000: base_split_amount = 2500000
            elif premium >= 150000: base_split_amount = 1500000
            elif premium >= 70000: base_split_amount = 700000
            base_split_rate = (base_split_amount / premium) if premium > 0 else 0.0
            
            cont_amount = 0
            cont_desc_parts = []
            if premium >= 250000: cont_amount += 960000; cont_desc_parts.append("연속가동① 96만")
            elif premium >= 150000: cont_amount += 660000; cont_desc_parts.append("연속가동① 66만")
            elif premium >= 70000: cont_amount += 420000; cont_desc_parts.append("연속가동① 42만")
                
            if premium >= 250000: cont_amount += 600000; cont_desc_parts.append("집중연속② 60만")
            elif premium >= 150000: cont_amount += 400000; cont_desc_parts.append("집중연속② 40만")
            elif premium >= 70000: cont_amount += 240000; cont_desc_parts.append("집중연속② 24만")
                
            if premium >= 500000: cont_amount += 1500000; cont_desc_parts.append("멤버십 150만")
            elif premium >= 400000: cont_amount += 1200000; cont_desc_parts.append("멤버십 120만")
            elif premium >= 300000: cont_amount += 900000; cont_desc_parts.append("멤버십 90만")
            elif premium >= 200000: cont_amount += 600000; cont_desc_parts.append("멤버십 60만")
            elif premium >= 100000: cont_amount += 300000; cont_desc_parts.append("멤버십 30만")
                
            cont_rate = (cont_amount / premium) if premium > 0 else 0.0
            cont_desc = " + ".join(cont_desc_parts) + f" (총 +{cont_amount//10000}만 원)"
            
            applied_cont = cont_rate if (continuous_mode != "none" and continuous_mode != "") else 0.0
            basis = f"익월 250%({int(premium*next_m):,}원) + 1주차가동 {base_split_amount//10000}만 원({int(base_split_rate*100)}%)"
            if applied_cont > 0:
                basis += f" [연계·연속 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 합산]"
                
            return {
                "next_month": next_m,
                "split": base_split_rate + applied_cont,
                "total": next_m + base_split_rate + applied_cont,
                "basis": basis,
                "cont_bonus": cont_rate,
                "cont_desc": cont_desc
            }

    # 6. 라이나생명 (새로담는건강, 브레인케어, 치아/치매, 종신 완벽 판정)
    elif '라이나' in comp:
        if '새로담는' in prod or '브레인' in prod or ('건강' in prod and '종신' not in prod):
            next_m = 3.0
            base_split = 1.0
            split_amount = 0
            if premium >= 300000: split_amount = 5400000
            elif premium >= 200000: split_amount = 3400000
            elif premium >= 100000: split_amount = 1600000
            elif premium >= 50000: split_amount = 500000
                
            split_rate_from_amount = (split_amount / premium) if premium > 0 else 0.0
            core_rate = 4.0 if premium >= 100000 else 0.0
            
            cont_amount = 0
            if premium >= 300000: cont_amount = 900000
            elif premium >= 200000: cont_amount = 600000
            elif premium >= 100000: cont_amount = 200000
            elif premium >= 50000: cont_amount = 100000
            cont_rate = (cont_amount / premium) if premium > 0 else 0.0
            
            applied_cont = cont_rate if (continuous_mode != "none" and continuous_mode != "") else 0.0
            tot_split_rate = base_split + split_rate_from_amount + core_rate + applied_cont
            tot_rate = next_m + tot_split_rate
            
            basis = f"익월 300%({int(premium*next_m):,}원) + 13회차 {int((base_split+split_rate_from_amount+core_rate)*100)}%(기본100+구간{split_amount//10000}만+핵심담보{int(core_rate*100)}%)"
            if applied_cont > 0:
                basis += f" [10~11월 연속가동 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 합산]"
                
            return {
                "next_month": next_m,
                "split": tot_split_rate,
                "total": tot_rate,
                "basis": basis,
                "cont_bonus": cont_rate,
                "cont_desc": f"10~11월 연속가동 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 추가 합산 가능"
            }
        elif '치아' in prod or '치매' in prod or '암' in prod:
            next_m = 3.0
            split_amount = 0
            if premium >= 300000: split_amount = 1800000
            elif premium >= 200000: split_amount = 1000000
            elif premium >= 100000: split_amount = 400000
            elif premium >= 50000: split_amount = 150000
            split_rate = (split_amount / premium) if premium > 0 else 0.0
            tot_rate = next_m + split_rate
            basis = f"익월 300% + 13회차 구간 {split_amount//10000}만 원({int(split_rate*100)}%)"
            return {"next_month": next_m, "split": split_rate, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            if '7년' in term:
                return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (THE채우는종신 7년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '간편' in term or '간편' in prod:
                if '10년' in term:
                    return {"next_month": 3.0, "split": 1.5, "total": 4.5, "basis": "익월 300% + 13회차 150% (THE채우는종신 10년납 간편 450%)", "cont_bonus": 0.0, "cont_desc": ""}
                else:
                    return {"next_month": 2.5, "split": 1.0, "total": 3.5, "basis": "익월 250% + 13회차 100% (THE착한간편종신 350%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '10년' in term:
                return {"next_month": 3.0, "split": 6.5, "total": 9.5, "basis": "익월 300% + 13회차 650% (THE채우는종신 10년납 일반심사 950%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 2.5, "split": 1.0, "total": 3.5, "basis": "익월 250% + 13회차 100% (THE건강/착한간편종신 350%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 7. 미래에셋생명 (건강파트 익월 250% + 구간시상)
    elif '미래' in comp:
        if '연금' in prod:
            rate = 2.0 if premium >= 200000 else (1.0 if premium >= 100000 else 0.0)
            return {"next_month": rate, "split": 0.0, "total": rate, "basis": f"익월 {int(rate*100)}% (변액연금 강화형)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '변액' in prod or '약속' in prod:
            return {"next_month": 1.0, "split": 2.8, "total": 3.8, "basis": "익월 100% + 13회차 280% (변액종신 미래의약속 380%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '상속' in prod or '헤리티지' in prod:
            return {"next_month": 2.0, "split": 4.5, "total": 6.5, "basis": "익월 200% + 13회차 450% (상속종신 헤리티지 650%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '치아' in prod:
            return {"next_month": 1.0, "split": 1.0, "total": 2.0, "basis": "익월 100% + 13회차 100% (치아보험 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            next_m = 2.5
            split_amount = 0
            if premium >= 2000000: split_amount = 35700000
            elif premium >= 1500000: split_amount = 20700000
            elif premium >= 1000000: split_amount = 10700000
            elif premium >= 700000: split_amount = 9200000
            elif premium >= 500000: split_amount = 8200000
            elif premium >= 300000: split_amount = 5700000
            elif premium >= 200000: split_amount = 3600000
            elif premium >= 100000: split_amount = 1500000
            elif premium >= 50000: split_amount = 150000
            
            split_rate = (split_amount / premium) if premium > 0 else 0.0
            tot_rate = next_m + split_rate
            basis = f"익월 250%({int(premium*next_m):,}원) + 13회차 구간시상 {split_amount//10000}만 원({int(split_rate*100)}%) = 총 {int(tot_rate*100)}%"
            return {"next_month": next_m, "split": split_rate, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}

    # 8. KB라이프 (11월 공식 시책: 5.10.5 비갱신형 전용, 갱신형/비갱신형 구간시상 정밀 판정)
    elif 'kb' in comp:
        prod_low = product_name.replace(" ", "").lower()
        gubun_low = gubun.replace(" ", "").lower() if gubun else ""

        # 연금 / 종신 / 정기 라인업
        if '100세' in prod_low or ('든든' in prod_low and '연금' in prod_low):
            m_y = re.search(r'(\d+)\s*년', term)
            years = int(m_y.group(1)) if m_y else 10
            if years >= 10:
                return {"next_month": 2.0, "split": 5.0, "total": 7.0, "basis": "익월 200% + 13회차 500% (100세 든든 연금 10년납↑ 700%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (100세 든든 연금 5·7년납 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '트리플' in prod_low:
            return {"next_month": 2.0, "split": 2.0, "total": 4.0, "basis": "익월 200% + 13회차 200% (트리플레벨업 연금 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '경영인' in prod_low:
            return {"next_month": 1.0, "split": 1.5, "total": 2.5, "basis": "익월 100% + 13회차 150% (경영인정기Ⅲ 250%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '리턴' in prod_low:
            m_y = re.search(r'(\d+)\s*년', term)
            years = int(m_y.group(1)) if m_y else 10
            if years >= 10:
                return {"next_month": 2.0, "split": 2.0, "total": 4.0, "basis": "익월 200% + 13회차 200% (KB리턴종신 10년납↑ 400%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 2.0, "split": 1.0, "total": 3.0, "basis": "익월 200% + 13회차 100% (KB리턴종신 10년납미만 300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '약속플러스' in prod_low:
            return {"next_month": 3.0, "split": 0.0, "total": 3.0, "basis": "익월 300% (약속플러스종신 300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '넥스트' in prod_low:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (넥스트레벨업 연금 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '7년의약속' in prod_low:
            return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (7년의약속 250%)", "cont_bonus": 0.0, "cont_desc": ""}

        # 딱좋은 건강보험 상품군 (5.10.5, 3.10.5, 3.N.5, 딱좋은 0540, 골든라이프 간병 등)
        else:
            next_m = 3.0
            
            # 13회차 구간 시상금 (보험료 합산)
            gugan_amt = 0
            if premium >= 1000000: gugan_amt = 12000000
            elif premium >= 500000: gugan_amt = 8000000
            elif premium >= 400000: gugan_amt = 6800000
            elif premium >= 300000: gugan_amt = 5400000
            elif premium >= 200000: gugan_amt = 3600000
            elif premium >= 100000: gugan_amt = 1800000
            elif premium >= 50000: gugan_amt = 250000
            
            # 13회차 전략담보 시상금
            strat_amt = 0
            if premium >= 300000: strat_amt = 150000
            elif premium >= 200000: strat_amt = 100000
            elif premium >= 100000: strat_amt = 50000
            elif premium >= 50000: strat_amt = 20000
            
            # 5.10.5 및 3.10.5 상품은 비갱신형밖에 없으므로 갱신형 시상금(400%)은 전면 제외!
            is_5105 = ('5105' in prod_low or '5.10.5' in prod_low or '초경증' in prod_low or '3105' in prod_low or '3.10.5' in prod_low)
            is_renew = False
            if not is_5105:
                if '갱신' in gubun_low or '갱신형' in prod_low or '갱신' in prod_low:
                    is_renew = True
            
            renew_amt = 0
            if is_renew:
                if premium >= 300000: renew_amt = 1200000
                elif premium >= 200000: renew_amt = 800000
                elif premium >= 100000: renew_amt = 400000
                elif premium >= 50000: renew_amt = 200000
            
            tot_split_amt = gugan_amt + renew_amt + strat_amt
            split_rate = (tot_split_amt / premium) if premium > 0 else 0.0
            tot_rate = next_m + split_rate
            
            gugan_p = int(round((gugan_amt / premium) * 100)) if premium > 0 else 0
            renew_p = int(round((renew_amt / premium) * 100)) if premium > 0 else 0
            strat_p = int(round((strat_amt / premium) * 100)) if premium > 0 else 0
            
            if is_5105:
                basis = f"익월 300%({int(premium*next_m):,}원) + 13회차 구간 {gugan_amt//10000}만({gugan_p}%) + 전략담보 {strat_amt//10000}만({strat_p}%) = 총 {int(tot_rate*100)}% (5.10.5 비갱신형 전용: 갱신형 시상 제외)"
            elif is_renew:
                basis = f"익월 300%({int(premium*next_m):,}원) + 13회차 구간 {gugan_amt//10000}만({gugan_p}%) + 갱신형 {renew_amt//10000}만({renew_p}%) + 전략담보 {strat_amt//10000}만({strat_p}%) = 총 {int(tot_rate*100)}% (갱신형 기준)"
            else:
                basis = f"익월 300%({int(premium*next_m):,}원) + 13회차 구간 {gugan_amt//10000}만({gugan_p}%) + 전략담보 {strat_amt//10000}만({strat_p}%) = 총 {int(tot_rate*100)}% (비갱신형: 갱신형 시상 제외)"
                
            return {
                "next_month": next_m,
                "split": split_rate,
                "total": tot_rate,
                "basis": basis,
                "cont_bonus": 0.0,
                "cont_desc": ""
            }

    # 9. 동양생명
    elif '동양' in comp:
        if '알뜰' in prod:
            return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (알뜰플러스 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.0, "split": 3.0, "total": 5.0, "basis": "익월 200% + 13회차 300% (우리WON 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 10. 푸본현대생명
    elif '푸본' in comp:
        if '원픽' in prod:
            base_next = 3.5
            base_split = 1.5
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("푸본현대", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            basis = f"원수사 500%(익월350+13회150)"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and '7년' in term:
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (마이픽 건강 600%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 11. KDB생명
    elif 'kdb' in comp:
        if '행복세븐' in prod:
            return {"next_month": 4.0, "split": 2.0, "total": 6.0, "basis": "원수사 600% (익월 400% + 13회차 200% · 20년납 전용)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '행복플러스' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "총 800% (익월 400% + 13회차 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '서포트100' in prod:
            if '20년' in term:
                return {"next_month": 4.0, "split": 6.0, "total": 10.0, "basis": "총 1,000% (익월 400% + 13회차 600%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.0, "split": 4.0, "total": 7.0, "basis": "총 700% (익월 300% + 13회차 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['더블찬스', '버팀목']):
            return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200%", "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['라이프핏', '암만생각해도', '암보험']):
            return {"next_month": 5.0, "split": 7.0, "total": 12.0, "basis": "총 1,200% (익월 500% + 13회차 700%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['행복드림', '행복플러스up', '연금']):
            if any(t in term for t in ['10년미만', '10년납 미만', '미만']):
                return {"next_month": 1.5, "split": 0.0, "total": 1.5, "basis": "익월 150% (10년납 미만 150%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.5, "split": 1.0, "total": 4.5, "basis": "총 450% (익월 350% + 13회차 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (버팀목종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 12. ABL생명
    elif 'abl' in comp:
        if '더채움' in prod:
            return {"next_month": 3.0, "split": 5.0, "total": 8.0, "basis": "익월 300% + 13차월 500% (우리WON더채움종신 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '스테이블' in prod:
            if '7년' in term:
                return {"next_month": 3.0, "split": 2.0, "total": 5.0, "basis": "익월 300% + 13차월 200% (우리WON스테이블종신 7년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.0, "split": 4.0, "total": 7.0, "basis": "익월 300% + 13차월 400% (우리WON스테이블종신 10년납 이상 700%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['더드림', '드림종신']):
            if '7년' in term:
                return {"next_month": 3.0, "split": 1.5, "total": 4.5, "basis": "익월 300% + 13차월 150% (우리WON더드림종신 7년납 450%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif any(t in term for t in ['5년', '10년']):
                return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (우리WON더드림종신 5/10년납 200%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (우리WON더드림종신 15년납 이상 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '더블종신' in prod:
            if '7년' in term:
                return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (우리WON더블종신 7년납 250%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '10년' in term:
                return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (우리WON더블종신 10년납 200%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (우리WON더블종신 15년납 이상 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['간편건강', '3.10.5', '건강n더보장', '케어간병', '톡톡튀는', '더담은암']):
            return {"next_month": 2.5, "split": 8.0, "total": 10.5, "basis": "익월 250% + 13차월 800% (우리WON 건강/암/간병 10년납 이상 1,050%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '상속' in prod:
            return {"next_month": 2.0, "split": 2.0, "total": 4.0, "basis": "익월 200% + 13차월 200% (우리WON상속종신 전 납기 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '세븐' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "익월 400% + 13차월 400% (우리WON세븐종신 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13차월 300% (ABL생명 기본 보장성 600%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 13. 농협생명
    elif '농협' in comp:
        if '종신' in prod:
            return {"next_month": 4.5, "split": 1.5, "total": 6.0, "basis": "익월 450% + 13회차 150% (투스텝NH종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 5.0, "split": 12.0, "total": 17.0, "basis": "익월 500% + 13회차 1,200% (건강플러스통합 1,700%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 14. 교보생명
    elif '교보' in comp:
        # 1) (간편)3밸런스보장보험PLUS (일반/간편 동일 환산·시책)
        if '3밸런스' in prod:
            if '5년' in term:
                return {"next_month": 0.0, "split": 0.0, "total": 0.0, "basis": "3밸런스 5년납: 시상 지원 제외 (0%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif any(t in term for t in ['20년', '20년납']):
                return {"next_month": 2.5, "split": 4.5, "total": 7.0, "basis": "익월 250% + 13차월 450% (3밸런스보장보험PLUS 20년납 700% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}
            else:  # 7년~15년납 (7~9년, 10~14년, 15~19년)
                return {"next_month": 2.5, "split": 4.0, "total": 6.5, "basis": "익월 250% + 13차월 400% (3밸런스보장보험PLUS 7~15년납 650% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

        # 2) (간편)다시채움건강종신보험 (일반/간편 동일 시책)
        elif '다시채움' in prod:
            if any(t in term for t in ['10년미만', '10년납 미만', '미만']):
                return {"next_month": 1.25, "split": 0.0, "total": 1.25, "basis": "익월 125% (다시채움 10년납 미만 125% · 일반/간편 동일 시책)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 2.5, "split": 2.5, "total": 5.0, "basis": "익월 250% + 13차월 250% (다시채움 10년납 이상 500% · 일반/간편 동일 시책)", "cont_bonus": 0.0, "cont_desc": ""}

        # 3) (간편)실속건강종신보험 (일반/간편 동일 시책)
        elif '실속건강' in prod:
            if any(t in term for t in ['10년미만', '10년납 미만', '미만']):
                return {"next_month": 0.75, "split": 0.0, "total": 0.75, "basis": "익월 75% (실속건강종신 10년납 미만 75% · 일반/간편 동일 시책)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 1.5, "split": 2.0, "total": 3.5, "basis": "익월 150% + 13차월 200% (실속건강종신[저해지] 10년납 이상 350% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

        # 4) (간편)경영인정기보험 (일반/간편 동일 시책)
        elif '경영인' in prod:
            return {"next_month": 2.7, "split": 2.3, "total": 5.0, "basis": "익월 270% + 13차월 230% (경영인정기 500% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

        # 5) (간편)밸런스건강보험 (일반/간편 동일 시책)
        elif '밸런스건강' in prod:
            return {"next_month": 2.5, "split": 0.5, "total": 3.0, "basis": "익월 250% + 13차월 50% (밸런스건강보험 10년납 이상 300% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

        # 6) (간편)모두지킴종신보험 (일반/간편 동일 시책)
        elif '모두지킴' in prod:
            return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13차월 300% (모두지킴종신 7~12년납 600% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

        # 7) 기타 교보 기본 보장성 (평생건강, K-실속종신, K-밸류업, 치매간병안심 등)
        else:
            return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (교보 보장성 기본 600% · 일반/간편 동일)", "cont_bonus": 0.0, "cont_desc": ""}

    # 15. 하나생명
    elif '하나' in comp:
        return {"next_month": 5.0, "split": 19.0, "total": 24.0, "basis": "익월 500% + 13회차 1,900% (하나로라이트 최대 2,400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 16. IM라이프
    elif 'im' in comp or '아이엠' in comp:
        if '당당한' in prod:
            base_next = 3.0 if '7년' in term else 2.5
            base_split = 1.0 if '7년' in term else 0.0
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("IM라이프", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and '7년' in term:
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 2.5, "total": 5.0, "basis": "익월 250% + 13회차 250% (IM라이프 주력 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (기본 전략 600%)", "cont_bonus": 0.0, "cont_desc": ""}


def calculate_life(
    company: str,
    product_name: str,
    premium: int,
    s_factor: float = 1000.0,
    term: str = "20년납",
    incentive_type: str = "전략",
    continuous_mode: str = "none",
    contract_type: str = "개인",
    gubun: str = ""
) -> Dict[str, Any]:
    comp_clean = company.replace('생명', '').replace('라이프', '').strip()
    
    conversion_rate = s_factor / 10.0
    s_grade = round(premium * (s_factor / 1000.0))
    
    next_month_rate = LIFE_RULES['next_month_rate']
    
    comp_inst_dict = LIFE_RULES.get('company_installments', {}).get(comp_clean, {})
    inst_rate = 1.32
    if isinstance(comp_inst_dict, dict):
        inst_rate = comp_inst_dict.get('default', 1.32)
        prod_lower = product_name.lower()
        for k, v in comp_inst_dict.items():
            if k != 'default' and k in prod_lower:
                inst_rate = v
                break
    elif isinstance(comp_inst_dict, (int, float)):
        inst_rate = float(comp_inst_dict)
        
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = next_month_comm + installment_comm
    
    inc_info = get_life_incentive(comp_clean, product_name, term, premium, incentive_type, continuous_mode, contract_type=contract_type, gubun=gubun)
    next_month_inc_rate = inc_info.get("next_month", 0.0)
    split_inc_rate = inc_info.get("split", 0.0)
    basis_desc = inc_info.get("basis", "")
    cont_bonus_rate = inc_info.get("cont_bonus", 0.0)
    cont_desc = inc_info.get("cont_desc", "")
    c1_amount = inc_info.get("c1_amount", 0)
    c2_amount = inc_info.get("c2_amount", 0)
    is_heungkuk = inc_info.get("is_heungkuk", False)
    
    next_month_inc = round(premium * next_month_inc_rate)
    split_inc = round(premium * split_inc_rate)
    total_inc = next_month_inc + split_inc
    total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    display_comp = company
    if not display_comp.endswith("생명") and not display_comp.endswith("라이프"):
        display_comp += "생명"
        
    return {
        "category": "생명보험",
        "company": display_comp,
        "product_name": product_name,
        "term": term,
        "premium": premium,
        "s_factor": s_factor,
        "conversion_rate": conversion_rate,
        "s_grade": s_grade,
        "next_month_comm": next_month_comm,
        "next_month_comm_rate": round(next_month_rate * 100, 1),
        "installment_comm": installment_comm,
        "installment_comm_rate": round(inst_rate * 100, 1),
        "total_comm": total_comm,
        "next_month_inc": next_month_inc,
        "next_month_inc_rate": round(next_month_inc_rate * 100, 1),
        "split_inc": split_inc,
        "split_inc_rate": round(split_inc_rate * 100, 1),
        "total_inc": total_inc,
        "total_inc_rate": total_inc_rate,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total,
        "basis_desc": basis_desc,
        "cont_bonus_rate": cont_bonus_rate,
        "cont_desc": cont_desc,
        "c1_amount": c1_amount,
        "c2_amount": c2_amount,
        "is_heungkuk": is_heungkuk,
        "continuous_mode": continuous_mode
    }


def calculate_company_for_compare(comp: str, premium: int, utterance: str, continuous_mode: str = "none") -> Dict[str, Any]:
    info = ALL_COMPANIES.get(comp, {})
    if info.get("category") == "손해보험":
        m_week = re.search(r'([1-5])\s*주차?', utterance)
        req_w = f"{m_week.group(1)}주차" if m_week else None
        return calculate_nonlife(comp, "주력보종", premium, "주력", continuous_mode, requested_week=req_w)
    else:
        candidates = find_candidate_products(comp, utterance)
        prod = candidates[0] if candidates else None
        p_name = clean_prod_short_name(prod['full_product']) if prod else info.get("default_prod", "보장성")
        gubun = match_gubun_in_text(prod, utterance) if prod else None
        if not gubun and prod and prod.get("gubuns"):
            gubun = prod["gubuns"][0]
        term = prod.get("terms", ["20년납"])[0] if prod else "20년납"
        s_factor = 1000.0
        if prod:
            item = match_master_item(prod, term, gubun or "")
            s_factor = item.get('s_factor', 1000.0)
        return calculate_life(comp, p_name, premium, s_factor=s_factor, term=term, gubun=gubun or "", continuous_mode=continuous_mode)


def calculate_nonlife(
    company: str,
    product_name: str,
    premium: int,
    incentive_type: str = "주력",
    continuous_mode: str = "none",
    requested_week: Optional[str] = None
) -> Dict[str, Any]:
    resolved_week, period_str, is_fallback, week_comps = resolve_nonlife_week(requested_week)

    comp_matched = "현대해상"
    for c in NONLIFE_RULES['companies']:
        if c in company or company in c:
            comp_matched = c
            break
            
    conv_rate = NONLIFE_RULES['conversion_rate']
    s_grade = round(premium * conv_rate)
    
    next_month_rate = NONLIFE_RULES['next_month_rate']
    inst_rate = NONLIFE_RULES['installment_rate']
    
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = next_month_comm + installment_comm
    
    comp_week_info = week_comps.get(comp_matched, {})
    comp_is_fallback = is_fallback
    comp_period = period_str
    comp_week = resolved_week

    if not comp_week_info:
        # 해당 주차에 이 회사의 전단지가 아직 업로드되지 않은 경우 1주차로 폴백
        w1_data = NONLIFE_WEEKLY_DATA.get("weeks", {}).get("1주차", {})
        comp_week_info = w1_data.get("companies", {}).get(comp_matched, {})
        comp_is_fallback = True
        comp_period = w1_data.get("period", "11.01 ~ 11.08")
        comp_week = "1주차"

    flyer_file = comp_week_info.get("flyer", ALL_COMPANIES.get(comp_matched, {}).get("flyer", f"{comp_matched}_1주.jpg"))
    inc_dict = comp_week_info.get(incentive_type, {})
    
    if not inc_dict:
        inc_dict = NONLIFE_RULES.get('incentives', {}).get(comp_matched, {}).get(incentive_type, {})
    if not inc_dict:
        inc_dict = NONLIFE_RULES.get('incentives', {}).get('현대해상', {}).get('주력', {})
        
    next_month_inc_rate = inc_dict.get('next_month_base', 1.0) + inc_dict.get('next_month_sky', 2.6)
    split_inc_rate = (
        inc_dict.get('install_week_bonus', 0.0) +
        inc_dict.get('install_main_bonus', 0.0) +
        inc_dict.get('install_sky_2nd', 0.0) +
        inc_dict.get('install_sky_add', 0.0)
    )
    
    basis_desc = inc_dict.get('basis', '')
    cont_bonus_rate = inc_dict.get('cont_bonus_rate', 0.0)
    cont_desc = inc_dict.get('cont_desc', '')
    
    include_cont = (continuous_mode != "none" and continuous_mode != "")
    if include_cont and cont_bonus_rate > 0:
        split_inc_rate += cont_bonus_rate
        basis_desc += f" [전월 연속가동 +{int(round(cont_bonus_rate*100))}% 합산]"
        
    next_month_inc = round(premium * next_month_inc_rate)
    split_inc = round(premium * split_inc_rate)
    total_inc = next_month_inc + split_inc
    total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    full_comp_name = comp_matched
    if not full_comp_name.endswith("해상") and not full_comp_name.endswith("손보") and not full_comp_name.endswith("화재"):
        full_comp_name += "화재"
        
    return {
        "category": "손해보험",
        "company": full_comp_name,
        "product_name": product_name,
        "term": "장기보장성",
        "premium": premium,
        "s_factor": 920.0,
        "conversion_rate": 92.0,
        "s_grade": s_grade,
        "next_month_comm": next_month_comm,
        "next_month_comm_rate": round(next_month_rate * 100, 1),
        "installment_comm": installment_comm,
        "installment_comm_rate": round(inst_rate * 100, 1),
        "total_comm": total_comm,
        "next_month_inc": next_month_inc,
        "next_month_inc_rate": round(next_month_inc_rate * 100, 1),
        "split_inc": split_inc,
        "split_inc_rate": round(split_inc_rate * 100, 1),
        "total_inc": total_inc,
        "total_inc_rate": total_inc_rate,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total,
        "basis_desc": basis_desc,
        "cont_bonus_rate": cont_bonus_rate,
        "cont_desc": cont_desc,
        "is_heungkuk": False,
        "continuous_mode": continuous_mode,
        "week": comp_week,
        "period": comp_period,
        "is_fallback": comp_is_fallback,
        "flyer": flyer_file
    }


# ==========================================
# 2. 시책지 원본 매핑 및 검색 (KB라이프, 신한라이프 등 완벽 수정)
# ==========================================
FLYER_MAP = {
    "신한라이프": "신한라이프_11월_p2.png",
    "신한생명": "신한라이프_11월_p2.png",
    "신한": "신한라이프_11월_p2.png",
    "KB라이프": "KB라이프_11월.png",
    "KB생명": "KB라이프_11월.png",
    "케이비라이프": "KB라이프_11월.png",
    "케이비생명": "KB라이프_11월.png",
    "라이나생명": "라이나생명_11월.png",
    "라이나": "라이나생명_11월.png",
    "한화생명": "한화생명_11월.png",
    "한화": "한화생명_11월.png",
    "흥국생명": "흥국생명_11월.png",
    "흥국": "흥국생명_11월.png",
    "DB생명": "DB생명_11월.jpg",
    "동부생명": "DB생명_11월.jpg",
    "디비생명": "DB생명_11월.jpg",
    "DB손해보험": "DB손보_1주.jpg",
    "DB손보": "DB손보_1주.jpg",
    "디비손보": "DB손보_1주.jpg",
    "디비": "DB손보_1주.jpg",
    "현대해상": "현대해상_1주.png",
    "현대": "현대해상_1주.png",
    "KB손보": "KB손보_1주차.jpg",
    "KB손해보험": "KB손보_1주차.jpg",
    "한화손보": "한화손보_1주.jpg",
    "한화손해보험": "한화손보_1주.jpg",
    "메리츠": "메리츠_11월_1주.jpg",
    "메리츠화재": "메리츠_11월_1주.jpg",
    "동양생명": "동양생명_11월.png",
    "동양": "동양생명_11월.png",
    "교보생명": "교보생명_11월.png",
    "교보": "교보생명_11월.png",
    "농협생명": "농협생명_11월.png",
    "농협": "농협생명_11월.png",
    "KDB생명": "KDB생명_11월.jpg",
    "KDB": "KDB생명_11월.jpg",
    "푸본현대": "푸본현대_11월.png",
    "푸본": "푸본현대_11월.png",
    "미래에셋": "미래에셋_11월.png",
    "미래": "미래에셋_11월.png",
    "메트라이프": "메트라이프_11월.jpg",
    "메트": "메트라이프_11월.jpg",
    "ABL생명": "ABL생명_11월.png",
    "ABL": "ABL생명_11월.png",
    "하나생명": "하나생명_11월.png",
    "IBK연금": "IBK연금_11월.png",
    "IM라이프": "IM라이프_11월.png",
    "롯데손보": "롯데손보_1주.jpg",
    "롯데": "롯데손보_1주.jpg",
    "하나손보": "하나손보_1주.jpg",
    "하나손해보험": "하나손보_1주.jpg",
    "농협손보": "농협손보_1주.jpg",
    "농협손해보험": "농협손보_1주.jpg",
    "흥국화재": "흥국화재_1주.jpg"
}

def find_flyer(comp_name: str, week: Optional[str] = None) -> Tuple[str, str]:
    c_norm = comp_name.replace(" ", "").lower()

    # 1. 주차별 손보 전단지 우선 확인 (week 지정 또는 자동 활성 주차)
    resolved_week, _, _, week_comps = resolve_nonlife_week(week)
    for c in week_comps:
        if c in comp_name or comp_name in c or c.replace(" ", "").lower() in c_norm or c_norm in c.replace(" ", "").lower():
            fn = week_comps[c].get("flyer")
            if fn:
                return c, fn

    if "kb생명" in c_norm or "kb라이프" in c_norm or "케이비생명" in c_norm or "케이비라이프" in c_norm:
        return "KB라이프", "KB라이프_11월.png"
    if "신한생명" in c_norm or "신한라이프" in c_norm or c_norm == "신한":
        return "신한라이프", "신한라이프_11월_p2.png"
    if "kb손" in c_norm:
        return "KB손해보험", "KB손보_1주차.jpg"
    if "db생명" in c_norm or "동부생명" in c_norm or "디비생명" in c_norm:
        return "DB생명", "DB생명_11월.jpg"
    if "db손" in c_norm or "동부화재" in c_norm or "디비손" in c_norm:
        return "DB손해보험", "DB손보_1주.jpg"
    if "흥국생명" in c_norm:
        return "흥국생명", "흥국생명_11월.png"
    if "흥국화재" in c_norm:
        return "흥국화재", "흥국화재_1주.jpg"
    if "한화생명" in c_norm:
        return "한화생명", "한화생명_11월.png"
    if "한화손" in c_norm:
        return "한화손해보험", "한화손보_1주.jpg"
    if "미래" in c_norm:
        return "미래에셋", "미래에셋_11월.png"
    if "라이나" in c_norm:
        return "라이나생명", "라이나생명_11월.png"
    if "메트" in c_norm:
        return "메트라이프", "메트라이프_11월.jpg"

    for k, v in FLYER_MAP.items():
        if k == comp_name or k.replace(" ", "").lower() == c_norm:
            return k, v
            
    sorted_keys = sorted(FLYER_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_keys:
        if k in comp_name or comp_name in k:
            return k, FLYER_MAP[k]
            
    return comp_name, "SKY_11월.jpg"


def build_flyer_response(comp_name: str, week: Optional[str] = None) -> Dict[str, Any]:
    matched_k, filename = find_flyer(comp_name, week=week)
    encoded_comp = urllib.parse.quote(matched_k)
    encoded_filename = urllib.parse.quote(filename)
    week_param = f"?week={urllib.parse.quote(week)}" if week else ""
    flyer_url = f"https://skyblue-kakao-bot.onrender.com/flyer/{encoded_comp}{week_param}"
    img_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_filename}"
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": f"📑 {matched_k} 11월 공식 시책지",
                        "description": "아래 [시책지 원본 열기]를 누르시면 고화질로 확대해 보실 수 있습니다.",
                        "thumbnail": {
                            "imageUrl": img_url
                        },
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "🔍 시책지 원본 열기",
                                "webLinkUrl": flyer_url
                            }
                        ]
                    }
                }
            ],
            "quickReplies": [
                {"messageText": "사용법", "action": "message", "label": "💡 사용법 (회사 상품 금액)"},
                {"messageText": f"{matched_k} 10만원", "action": "message", "label": f"{matched_k} 10만 계산"},
                {"messageText": f"{matched_k} 20만원", "action": "message", "label": f"{matched_k} 20만 계산"},
                {"messageText": "도움말", "action": "message", "label": "💡 도움말"}
            ]
        }
    }


# ==========================================
# 3. 대화형 되묻기 인터랙션 (회사만 / 금액누락 / 생보사 납기질의 / 흥국연속질의)
# ==========================================
def get_suggested_terms_for_life(comp: str, prod_name: str) -> List[str]:
    """생보사 상품별 최적화된 추천 납기 목록 생성 (사용자 지시: 납기 질의 및 메트라이프 납기별 차이 완벽 지원)"""
    c = comp.replace("생명", "").replace("라이프", "").strip()
    p = prod_name.replace(" ", "").lower()
    
    if c == "메트" or "달러" in p or "백만인" in p:
        return ["5년납(250%)", "7년납(400%)", "10년납(400%)", "15년납", "20년납"]
    elif "라이나" in c and ("종신" in p or "채우는" in p):
        return ["10년납 일반(950%)", "10년납 간편(450%)", "7년납(500%)", "착한간편종신(350%)"]
    elif "건강더한" in p:
        return ["7년납", "10년납", "15년납", "20년납"]
    elif "하나로" in p:
        return ["10년납", "15년납(법인시상)", "20년납"]
    elif "원픽" in p:
        return ["5년납", "7년납(법인시상)", "20년납"]
    elif "당당한" in p:
        return ["5년납", "7년납(법인시상)", "20년납"]
    elif "필요할때" in p:
        return ["10년납", "12년납", "15년납", "20년납"]
    elif "알행플" in p or "알행종" in p:
        return ["7년납(SKY시상)", "10년납(SKY시상)", "15년납", "20년납"]
    elif "쑥쑥" in p or "어린이" in p:
        return ["15년납", "20년납", "30년납"]
    elif "연금" in p:
        return ["10년납", "15년납", "20년납", "전기납"]
    elif "오튼튼" in p or "다사랑" in p or "3.10.5" in p:
        return ["10년납", "15년납", "20년납", "30년납"]
    elif "리턴100" in p:
        return ["10년납", "15년납", "20년납"]
    else:
        return ["10년납", "15년납", "20년납", "30년납"]


BRAND_PREFIXES = [
    r'^백년친구\s*',
    r'^우리WON하는\s*',
    r'^우리WON\s*',
    r'^골든라이프\s*',
    r'^iM\s*',
    r'^NH올원\s*',
    r'^NH\s*',
    r'^KB\s*',
    r'^K-\s*',
    r'^교보\(간편\)\s*',
    r'^교보\s*',
]

def make_similar_btn_label(num: int, prod_name: str) -> str:
    p = prod_name
    for bp in BRAND_PREFIXES:
        p = re.sub(bp, '', p)
    label = f"{num}. {p}"
    if len(label) > 13:
        m = re.search(r'\((.*?)\)$', label)
        if m:
            type_str = m.group(1)
            base = re.sub(r'\s*\(.*?\)$', '', label)
            avail = 13 - len(f"({type_str})") - 1
            if avail > 3:
                label = f"{base[:avail]}…({type_str})"
            else:
                label = label[:12] + "…"
        else:
            label = label[:12] + "…"
    return label

def build_ask_similar_product_response(comp: str, candidates: list, premium: int, term: str = "", gubun: str = "") -> dict:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"

    quick_replies = []
    for i, c in enumerate(candidates[:6]):
        short_name = clean_prod_short_name(c['full_product'])
        btn_label = make_similar_btn_label(i+1, short_name)
        msg_parts = [comp, short_name]
        if gubun: msg_parts.append(gubun)
        if term: msg_parts.append(term)
        msg_parts.append(prem_str)
        quick_replies.append({
            "messageText": " ".join(msg_parts),
            "action": "message",
            "label": btn_label
        })
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법"})

    prod_list_text = "\n".join([f"{i+1}. {clean_prod_short_name(c['full_product'])}" for i, c in enumerate(candidates[:6])])
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"🔍 {comp} ({prem_str})\n\n유사한 상품이 여러 개 있습니다. 어떤 상품으로 계산해 드릴까요?\n\n{prod_list_text}\n\n원하시는 상품 버튼을 눌러주세요!"
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }

def build_ask_gubun_response(comp: str, prod_group: dict, premium: int, term: str = "") -> dict:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    prod_name = clean_prod_short_name(prod_group['full_product'])

    quick_replies = []
    for g in prod_group['gubuns'][:6]:
        btn_label = g
        if len(btn_label) > 13:
            btn_label = btn_label[:12] + "…"
        msg_parts = [comp, prod_name, g]
        if term: msg_parts.append(term)
        msg_parts.append(prem_str)
        quick_replies.append({
            "messageText": " ".join(msg_parts),
            "action": "message",
            "label": btn_label
        })
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법"})

    is_kb_health = ('kb' in comp.lower() and ('딱좋은' in prod_name or '건강' in prod_name))
    if is_kb_health:
        info_text = (
            f"📋 {comp} · {prod_name} ({prem_str})\n\n"
            f"이 상품은 갱신형 여부('종')에 따라 갱신형 시상금(+400%) 및 환산 성적이 다릅니다. 어떤 구분을 적용할까요?\n\n"
            f"• 비갱신형 (해약환급금 미지급형)\n"
            f"• 갱신형\n\n"
            f"원하시는 구분 버튼을 눌러주세요!"
        )
    else:
        gubun_list_text = "\n".join([f"• {g}" for g in prod_group['gubuns'][:6]])
        info_text = (
            f"📋 {comp} · {prod_name} ({prem_str})\n\n"
            f"이 상품은 가입 유형('종')에 따라 환산 성적이 다릅니다. 어떤 구분을 적용할까요?\n\n"
            f"{gubun_list_text}\n\n"
            f"원하시는 구분 버튼을 눌러주세요!"
        )

    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": info_text
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }

def build_ask_term_response(comp: str, prod_name: str, premium: int, terms: List[str], gubun: str = "", invalid_term: Optional[str] = None) -> Dict[str, Any]:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    clean_prod = clean_prod_short_name(prod_name)
    
    quick_replies = []
    for t in terms[:8]:
        clean_t = re.sub(r'\(.*?\)', '', t).strip()
        btn_label = clean_t
        if len(btn_label) > 13:
            btn_label = btn_label[:12] + "…"
        msg_parts = [comp, clean_prod]
        if gubun: msg_parts.append(gubun)
        msg_parts.extend([prem_str, clean_t])
        quick_replies.append({
            "messageText": " ".join(msg_parts),
            "action": "message",
            "label": btn_label
        })
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법 안내"})
    
    gubun_str = f" · {gubun}" if gubun else ""
    if invalid_term:
        guide_text = f"⚠️ {comp} · {clean_prod}{gubun_str} ({prem_str})\n\n해당 상품은 '{invalid_term}'이(가) 조견표에 없습니다.\n\n아래 실제 납기 버튼을 누르시면 해당 납기로 즉시 계산됩니다!"
    else:
        guide_text = f"📋 {comp} · {clean_prod}{gubun_str} ({prem_str})\n\n생명보험사는 납입기간(*년납)에 따라 S환산 성적과 시상률이 다릅니다. 몇 년납으로 계산해 드릴까요?\n\n원하시는 납기 버튼을 누르시거나 직접 입력해 주세요!"
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": guide_text
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }

def is_corp_incentive_target(comp: str, prod_name: str, term: str = "") -> bool:
    """한화생명 하나로(15년), 푸본현대 맥스원픽(7년), IM라이프 당당한인생(7년) 3개 상품은 법인계약만 추가지급 대상인지 확인"""
    c = comp.lower()
    p = prod_name.replace(" ", "").lower()
    t = term.replace(" ", "").lower()
    if ('한화' in c) and ('하나로' in p):
        return ('15' in t) if t else True
    if ('푸본' in c) and ('원픽' in p):
        return ('7' in t) if t else True
    if ('im' in c or '아이엠' in c) and ('당당한' in p):
        return ('7' in t) if t else True
    return False

def build_ask_contract_type_response(comp: str, prod_name: str, premium: int, term: str, gubun: str = "") -> Dict[str, Any]:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    clean_prod = clean_prod_short_name(prod_name)
    term_str = f" · {term}" if term else ""
    gubun_str = f" · {gubun}" if gubun else ""
    
    msg_base = [comp, clean_prod]
    if gubun: msg_base.append(gubun)
    if term: msg_base.append(term)
    msg_base.append(prem_str)
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": (
                            f"📋 {comp} · {clean_prod}{gubun_str} ({prem_str}{term_str})\n\n"
                            "본 상품의 SKY 본사 추가 시상은 **법인계약**에만 지급됩니다.\n"
                            "계약자가 개인인가요, 법인인가요?\n\n"
                            "아래 버튼을 눌러 선택해 주세요!"
                        )
                    }
                }
            ],
            "quickReplies": [
                {
                    "messageText": " ".join(msg_base + ["법인계약"]),
                    "action": "message",
                    "label": "🏢 법인계약 (SKY시상 포함)"
                },
                {
                    "messageText": " ".join(msg_base + ["개인계약"]),
                    "action": "message",
                    "label": "👤 개인계약"
                },
                {
                    "messageText": "사용법",
                    "action": "message",
                    "label": "💡 사용법 안내"
                }
            ]
        }
    }

def build_compare_response(results: List[Dict[str, Any]], premium: int, continuous_mode: str = "none") -> Dict[str, Any]:
    prem_man = premium // 10000
    sorted_results = sorted(results, key=lambda x: x['grand_total'], reverse=True)
    diff = sorted_results[0]['grand_total'] - sorted_results[-1]['grand_total']
    winner = sorted_results[0]['company']
    
    ranks = ["🥇 1위", "🥈 2위", "🥉 3위"]
    item_list = []
    for i, r in enumerate(sorted_results):
        rank_label = ranks[i] if i < len(ranks) else f"{i+1}위"
        p_name = r.get('product_name', '')
        if len(p_name) > 10:
            p_name = p_name[:9] + "…"
        item_list.append({
            "title": f"{rank_label} {r['company']}",
            "description": f"{r['grand_total']:,}원"
        })
        
    buttons = []
    for r in sorted_results[:2]:
        buttons.append({
            "label": f"🔍 {r['company']} 상세 계산",
            "action": "message",
            "messageText": f"{r['company']} {r.get('product_name', '')} {prem_man}만원"
        })
        
    comp_names = " vs ".join(r['company'] for r in sorted_results)
    title_desc = f"{comp_names} 총합(수수료+시상) 비교"
    
    quick_replies = [
        {"messageText": f"{comp_names} 10만 비교", "action": "message", "label": "10만 비교"},
        {"messageText": f"{comp_names} 20만 비교", "action": "message", "label": "20만 비교"},
        {"messageText": f"{comp_names} 30만 비교", "action": "message", "label": "30만 비교"},
        {"messageText": f"{comp_names} {prem_man}만 연속포함 비교", "action": "message", "label": "🔥 연속시상 포함"},
        {"messageText": "도움말", "action": "message", "label": "💡 사용법"}
    ]
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": f"⚖️ {prem_man}만 원 판매 시 총수령액 비교",
                            "description": title_desc
                        },
                        "title": f"🏆 최고: {winner} (+{diff:,}원)",
                        "itemList": item_list,
                        "itemListSummary": {
                            "title": "1위 vs 최하위 격차",
                            "description": f"{diff:,}원"
                        },
                        "buttons": buttons
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


# ==========================================
# 5. 미답변 질문 표준 폴백 안내 (사용자 지정 문구)
# ==========================================
def build_fallback_response() -> Dict[str, Any]:
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "회사명 상품명 금액 을 입력해주세요\n(예: 한화생명 건강더한종신 100만)"
                    }
                }
            ],
            "quickReplies": [
                {"messageText": "한화생명 건강더한종신 100만", "action": "message", "label": "한화 건강더한 100만"},
                {"messageText": "흥국생명 오튼튼 20만 20년납", "action": "message", "label": "흥국 오튼튼 20만"},
                {"messageText": "메트라이프 달러종신 20만 10년납", "action": "message", "label": "메트 달러종신 20만"},
                {"messageText": "현대해상 주력 20만", "action": "message", "label": "현대 주력 20만"},
                {"messageText": "DB손보 10만원", "action": "message", "label": "DB손보 10만"},
                {"messageText": "신한라이프 통합건강 20만", "action": "message", "label": "신한 통합건강 20만"},
                {"messageText": "라이나 새로담는건강 20만", "action": "message", "label": "라이나 새로담는 20만"},
                {"messageText": "흥국 vs 현대 20만 비교", "action": "message", "label": "흥국 vs 현대 20만 비교"}
            ]
        }
    }


def build_kakao_response(calc_result: Dict[str, Any]) -> Dict[str, Any]:
    cat = calc_result.get("category", "")
    comp = calc_result.get("company", "")
    prod = calc_result.get("product_name", "")
    prem = calc_result.get("premium", 0)
    term = calc_result.get("term", "")
    
    prem_man = prem // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{prem:,}원"
    
    conv_rate = calc_result.get("conversion_rate", 0.0)
    s_grade = calc_result.get("s_grade", 0)
    
    next_comm = calc_result.get("next_month_comm", 0)
    next_comm_rate = calc_result.get("next_month_comm_rate", 0.0)
    inst_comm = calc_result.get("installment_comm", 0)
    inst_comm_rate = calc_result.get("installment_comm_rate", 0.0)
    tot_comm = calc_result.get("total_comm", 0)
    
    next_inc = calc_result.get("next_month_inc", 0)
    next_inc_rate = calc_result.get("next_month_inc_rate", 0.0)
    split_inc = calc_result.get("split_inc", 0)
    split_inc_rate = calc_result.get("split_inc_rate", 0.0)
    tot_inc = calc_result.get("total_inc", 0)
    tot_inc_rate = calc_result.get("total_inc_rate", 0.0)
    
    tot_next = calc_result.get("total_next_month", 0)
    tot_split = calc_result.get("total_split", 0)
    grand_total = calc_result.get("grand_total", 0)
    
    basis_desc = calc_result.get("basis_desc", "")
    cont_bonus_rate = calc_result.get("cont_bonus_rate", 0.0)
    c1_amount = calc_result.get("c1_amount", 0)
    c2_amount = calc_result.get("c2_amount", 0)
    is_heungkuk = calc_result.get("is_heungkuk", False)
    c_mode = calc_result.get("continuous_mode", "none")
    
    item_list = [
        {"title": "월 보험료 (월납)", "description": f"{prem:,}원"},
        {"title": f"S환산성적 ({conv_rate:.1f}%)", "description": f"{s_grade:,}원"},
        {"title": f"수수료 합계", "description": f"{tot_comm:,}원"},
        {"title": f"  • 익월 ({next_comm_rate:.0f}%)", "description": f"{next_comm:,}원"},
        {"title": f"  • 분급 ({inst_comm_rate:.0f}%)", "description": f"{inst_comm:,}원"},
        {"title": f"시상금 합계 ({tot_inc_rate:.0f}%)", "description": f"{tot_inc:,}원"},
        {"title": f"  • 익월시상 ({next_inc_rate:.0f}%)", "description": f"{next_inc:,}원"},
        {"title": f"  • 13회차/분할 ({split_inc_rate:.0f}%)", "description": f"{split_inc:,}원"},
        {"title": "────────────────", "description": "──────────"},
        {"title": "⚡ 익월 총수령 (수수료+시상)", "description": f"{tot_next:,}원"},
        {"title": "⏳ 분할/13회 총수령", "description": f"{tot_split:,}원"}
    ]
    
    quick_replies = [
        {"messageText": "사용법", "action": "message", "label": "💡 사용법 (회사 상품 금액)"}
    ]
    
    if is_heungkuk:
        c1_man = c1_amount // 10000
        c2_man = c2_amount // 10000
        if c_mode != "none":
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} {term}".strip(),
                "action": "message",
                "label": "↩️ 단건 시상으로 보기"
            })
        if "c1" not in c_mode and "both" not in c_mode and "all" not in c_mode and c1_man > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 10-11월 연속포함".strip(),
                "action": "message",
                "label": f"🔥 10~11월연속 (+{c1_man}만)"
            })
        if "c2" not in c_mode and "both" not in c_mode and "all" not in c_mode and c2_man > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 핑크멤버스 포함".strip(),
                "action": "message",
                "label": f"🌸 핑크멤버스 (+{c2_man}만)"
            })
        if "both" not in c_mode and "all" not in c_mode and (c1_man + c2_man) > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 풀연속포함".strip(),
                "action": "message",
                "label": f"💎 둘다포함 (+{c1_man+c2_man}만)"
            })
    else:
        if cont_bonus_rate > 0:
            if c_mode != "none":
                quick_replies.append({
                    "messageText": f"{comp} {prod} {prem_str} {term}".strip(),
                    "action": "message",
                    "label": "↩️ 단건 시상으로 보기"
                })
            else:
                quick_replies.append({
                    "messageText": f"{comp} {prod} {prem_str} {term} 연속포함".strip(),
                    "action": "message",
                    "label": f"🔥 연속포함 (+{int(round(prem * cont_bonus_rate // 10000))}만)"
                })
            
    week = calc_result.get("week", "")
    period = calc_result.get("period", "")
    is_fallback = calc_result.get("is_fallback", False)
    
    if cat == "손해보험":
        quick_replies.extend([
            {"messageText": f"1주차 {comp} 10만원", "action": "message", "label": "1주차 계산"},
            {"messageText": f"2주차 {comp} 10만원", "action": "message", "label": "2주차 계산"},
            {"messageText": f"{comp} vs 현대 20만 비교", "action": "message", "label": "비교하기"}
        ])
    else:
        quick_replies.extend([
            {"messageText": f"{comp} {prod} 10만원 {term}".strip(), "action": "message", "label": "10만 계산"},
            {"messageText": f"{comp} {prod} 20만원 {term}".strip(), "action": "message", "label": "20만 계산"},
            {"messageText": f"{comp} vs 현대 20만 비교", "action": "message", "label": "비교하기"}
        ])
    
    basis_text = f"💡 시상 산출근거: {basis_desc}"
    if cat == "손해보험":
        if is_fallback:
            basis_text += f"\n(※ 현재 11월 1주차({period}) 기준이며, 월요일 오후~화요일 오전 2주차 시책지 업로드 시 즉시 자동 갱신됩니다)"
        elif period:
            basis_text += f"\n(※ 11월 {week} 시책 기준 [적용기간: {period}])"
    elif is_heungkuk and c_mode == "none":
        basis_text += f"\n(※ 10~11월 연속가동 또는 핑크멤버스 연속 시책은 아래 퀵버튼을 눌러 합산하실 수 있습니다)"
    elif not is_heungkuk and c_mode == "none" and cont_bonus_rate > 0:
        basis_text += f"\n(※ 전월 연속가동 시상은 아래 [🔥 연속포함] 버튼을 누르면 즉시 합산됩니다)"

    if cat == "손해보험":
        if is_fallback:
            card_desc = f"{clean_product_display_name(prod)} · 11월 {week}({period}) [2주차 대기]"
        else:
            card_desc = f"{clean_product_display_name(prod)} · 11월 {week}({period})"
        flyer_btn_label = f"📑 {comp} {week} 시책지 보기" if week else f"📑 {comp} 시책지 보기"
        flyer_query = f"?week={urllib.parse.quote(week)}" if week else ""
        flyer_btn_url = f"https://skyblue-kakao-bot.onrender.com/flyer/{urllib.parse.quote(comp)}{flyer_query}"
    else:
        card_desc = f"{clean_product_display_name(prod)} · {term}" if term else clean_product_display_name(prod)
        flyer_btn_label = f"📑 {comp} 시책지 보기"
        flyer_btn_url = f"https://skyblue-kakao-bot.onrender.com/flyer/{urllib.parse.quote(comp)}"
        
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": f"[{cat}] {comp}",
                            "description": card_desc
                        },
                        "title": f"총 수령액 {grand_total:,}원",
                        "itemList": item_list,
                        "itemListSummary": {
                            "title": "최종 합계 (수수료 + 시상)",
                            "description": f"{grand_total:,}원"
                        },
                        "buttons": [
                            {
                                "label": flyer_btn_label,
                                "action": "webLink",
                                "webLinkUrl": flyer_btn_url
                            }
                        ]
                    }
                },
                {
                    "simpleText": {
                        "text": basis_text
                    }
                }
            ],
            "quickReplies": quick_replies[:5]
        }
    }


def build_help_response() -> Dict[str, Any]:
    help_text = (
        "🤖 스카이블루에셋 정산 계산기\n\n"
        "회사명, 상품명, 금액을 입력하시면 익월/분급 수수료와 11월 공식 시상금을 즉시 계산해 드립니다.\n\n"
        "📌 [단건 계산 예시]\n"
        "• DB손보 10만원\n"
        "• 한화생명 건강더한종신 50만원 10년납\n"
        "• 메트라이프 달러종신 20만 10년납\n"
        "• 신한라이프 통합건강 20만 (연속포함)\n"
        "• 라이나 새로담는건강 20만\n"
        "• 흥국생명 오튼튼 20만 10-11월 연속\n"
        "• 미래에셋 M-케어건강 20만\n"
        "• 현대해상 주력 20만\n\n"
        "⚖️ [2~3개사 비교 예시]\n"
        "• 흥국 vs 현대 20만 비교\n"
        "• 흥국생명 현대해상 DB손보 20만 비교\n"
        "• 한화 vs 흥국 20만 비교\n\n"
        "💡 생명보험사는 금액 입력 시 납기(*년납)를 퀵버튼으로 먼저 여쭤봅니다!"
    )
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": help_text}}],
            "quickReplies": [
                {"messageText": "DB손보 10만원", "action": "message", "label": "DB손보 10만"},
                {"messageText": "한화생명 건강더한종신 50만원", "action": "message", "label": "한화 건강더한 50만"},
                {"messageText": "메트라이프 달러종신 20만", "action": "message", "label": "메트 달러종신 20만"},
                {"messageText": "신한라이프 통합건강 20만", "action": "message", "label": "신한 통합건강 20만"},
                {"messageText": "라이나 새로담는건강 20만", "action": "message", "label": "라이나 새로담는 20만"},
                {"messageText": "흥국 vs 현대 20만 비교", "action": "message", "label": "흥국 vs 현대 20만 비교"}
            ]
        }
    }


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "스카이블루에셋 카카오 챗봇 스킬 서버",
        "version": app.version,
        "total_life_products": len(LIFE_PRODUCTS)
    }


@app.get("/flyer-img/{filename}")
def get_flyer_img(filename: str):
    import os
    import urllib.parse
    from fastapi.responses import FileResponse, RedirectResponse
    path = os.path.join("flyers", filename)
    if os.path.exists(path):
        return FileResponse(path)
    encoded_fn = urllib.parse.quote(filename)
    raw_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_fn}"
    return RedirectResponse(raw_url)


@app.get("/flyer/{company_name}")
def view_flyer_html(company_name: str, week: Optional[str] = None):
    matched_k, filename = find_flyer(company_name, week=week)
    encoded_filename = urllib.parse.quote(filename)
    raw_cdn_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_filename}"
    local_img_url = f"/flyer-img/{filename}"
    week_str = f" ({week})" if week else ""
    
    if "신한" in matched_k:
        pages = ["신한라이프_11월_p1.png", "신한라이프_11월_p2.png", "신한라이프_11월_p3.png"]
        img_tags = "".join([f'<div style="margin-bottom:16px;"><img src="https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{p}" onerror="this.src=\'/flyer-img/{p}\'" alt="신한라이프 시책지 {i+1}페이지"><p style="text-align:center;font-size:12px;color:#94a3b8;margin:6px 0 20px;">[ {i+1} / 3 페이지 ]</p></div>' for i, p in enumerate(pages)])
    else:
        img_tags = f'<img src="{raw_cdn_url}" onerror="this.src=\'{local_img_url}\'" alt="{matched_k} 시책지">'
        
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>{matched_k} 11월{week_str} 공식 시책지</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .header {{
            position: sticky;
            top: 0;
            width: 100%;
            max-width: 800px;
            background-color: #1e293b;
            padding: 12px 16px;
            box-sizing: border-box;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            z-index: 100;
        }}
        .title {{
            font-size: 16px;
            font-weight: 700;
            margin: 0;
        }}
        .btn-group {{
            display: flex;
            gap: 8px;
        }}
        .action-btn {{
            background-color: #0284c7;
            color: white;
            text-decoration: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }}
        .action-btn.secondary {{
            background-color: #475569;
        }}
        .container {{
            width: 100%;
            max-width: 800px;
            padding: 8px 0;
            box-sizing: border-box;
        }}
        img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">📑 {matched_k} 11월 공식 시책지</h1>
        <div class="btn-group">
            <a class="action-btn secondary" href="{raw_cdn_url}" target="_blank">고화질 원본</a>
            <a class="action-btn" href="{local_img_url}" download>다운로드</a>
        </div>
    </div>
    <div class="container">
        {img_tags}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ==========================================
# 6. 메인 카카오 스킬 라우터
# ==========================================

# ==========================================
# 0-1. 관리자 REST API (최총무 앱 전용)
# ==========================================
@app.get("/admin/users")
def get_admin_users(key: str = ""):
    if key != "skyblue2026admin":
        return {"error": "unauthorized"}
    return AUTH_CACHE

@app.post("/admin/reload")
def admin_reload(key: str = ""):
    if key != "skyblue2026admin":
        return {"error": "unauthorized"}
    load_auth_db()
    return {"ok": True, "msg": "Auth DB reloaded from GitHub"}

@app.get("/admin/participants")
def get_admin_participants(key: str = ""):
    if key != "skyblue2026admin":
        return {"error": "unauthorized"}
    return {
        "participants": get_sorted_participants(),
        "blocked": list(AUTH_CACHE.get("blocked", {}).values()),
        "admins": AUTH_CACHE.get("admins", [])
    }

@app.post("/admin/block")
async def admin_block_user(request: Request):
    data = await request.json()
    if data.get("key") != "skyblue2026admin":
        return {"error": "unauthorized"}
    target = str(data.get("target", ""))
    ok, msg = block_user_by_target(target)
    return {"ok": ok, "msg": msg}

@app.post("/admin/unblock")
async def admin_unblock_user(request: Request):
    data = await request.json()
    if data.get("key") != "skyblue2026admin":
        return {"error": "unauthorized"}
    target = str(data.get("target", ""))
    ok, msg = unblock_user_by_target(target)
    return {"ok": ok, "msg": msg}

@app.post("/skill/calculate")
async def kakao_skill_calculate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return build_fallback_response()

    user_request = body.get("userRequest", {})
    utterance = user_request.get("utterance", "").strip()
    user = user_request.get("user", {})
    user_id = user.get("id", "")

    # [0단계] 관리자 등록 키워드 감지 (최정우 본부장님 카카오톡 연결)
    if any(k in utterance for k in ["관리자", "본부장"]) and any(k in utterance for k in ["최정우", "안양비전", "비전본부", "skyblue", "관리자", "등록"]):
        register_admin(user_id, "최정우 본부장 (Admin)")
        return build_admin_registered_response()

    # [1단계] 차단(강퇴) 계정 차단
    if is_blocked(user_id):
        return build_blocked_response()

    # [2단계] 관리자 전용 명령어 (명단, 강퇴, 차단목록, 차단해제)
    if is_admin(user_id):
        admin_res = handle_admin_command(utterance)
        if admin_res:
            return admin_res

    # [3단계] 참여자 활동 자동 기록 (초고속 로컬 0.0001초)
    track_participant(user_id, utterance)

    # [4단계] 계산 및 일반 대화 처리 (누구나 바로 이용!)
    if not utterance or utterance in ["도움말", "사용법", "메뉴", "시작", "help", "?"]:
        return build_help_response()

    try:
        # 1. 시책지 전단지 직접 요청 처리
        if any(kw in utterance for kw in ['시책지', '시책표', '전단지', '시책확인']):
            for k in FLYER_MAP.keys():
                if k in utterance:
                    return build_flyer_response(k)
            return build_flyer_response("스카이블루")

        # 2. 회사명 및 금액 추출
        matched_comps = find_companies_in_text(utterance)
        premium = parse_premium(utterance)
        # 계약자 형태 (개인 vs 법인) 추출
        contract_type = ""
        if any(k in utterance for k in ['법인', '법인계약']):
            contract_type = "법인"
        elif any(k in utterance for k in ['개인', '개인계약']):
            contract_type = "개인"
        
        # 연속시상 모드 판정
        continuous_mode = "none"
        if "핑크" in utterance:
            continuous_mode = "c2"
        elif any(kw in utterance for kw in ['10-11', '10월연속', '연속가동']):
            continuous_mode = "c1"
        elif any(kw in utterance for kw in ['풀', '모두', '둘다', '전체', '연속포함', '연속', '연계']):
            continuous_mode = "both"
            
        # 흥국생명 연속시상 질의 판정
        if any(k in utterance for k in ['흥국']) and any(kw in utterance for kw in ['연속시상', '연속얼마', '10월실적', '10월']) and premium is None:
            return build_heungkuk_continuous_inquiry_response()

        is_compare_query = (
            len(matched_comps) >= 2 or
            (len(matched_comps) >= 2 and any(k in utterance for k in ['비교', 'vs', 'VS', '대', '차이']))
        )

        # 3. 2개 또는 3개 회사 비교 처리 (총합만 비교하는 카드)
        if is_compare_query:
            target_comps = matched_comps[:3]
            comp_prem = premium or 200000
            comp_results = []
            for c in target_comps:
                res = calculate_company_for_compare(c, comp_prem, utterance, continuous_mode)
                comp_results.append(res)
            return build_compare_response(comp_results, comp_prem, continuous_mode)

        # 4. 단일 회사 처리
        if len(matched_comps) == 1:
            comp = matched_comps[0]
            
            cleaned = utterance
            for alias in ALL_COMPANIES[comp]['aliases']:
                cleaned = re.sub(re.escape(alias), '', cleaned, flags=re.IGNORECASE)
            cleaned_tokens = re.sub(r'[시책|계산|얼마|수수료|시상|조회|알려줘|해줘|\s|\?|\!|\.]', '', cleaned)
            
            # Case 4-A: 상품과 금액 없이 회사명만 입력한 경우 -> 둘 다 되묻기
            if premium is None and len(cleaned_tokens) == 0:
                return build_ask_product_and_amount_response(comp)
                
            # Case 4-B: 상품명은 있으나 금액이 없는 경우 -> 금액만 되묻기
            if premium is None:
                info = ALL_COMPANIES[comp]
                m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                term = m_term.group(0) if m_term else info.get("default_term", "")
                prod_name = cleaned_tokens if cleaned_tokens else info.get("default_prod", "주력")
                return build_ask_amount_response(comp, prod_name, term)
                
            # Case 4-C: 금액이 명시된 정상 단건 계산
            calc_prem = premium
            info = ALL_COMPANIES[comp]
            
            # 손해보험: 92% 고정 및 주차별 시책 즉시 계산
            if info['category'] == "손해보험":
                m_week = re.search(r'([1-5])\s*주차?', utterance)
                requested_week = f"{m_week.group(1)}주차" if m_week else None

                prod_name = "주력보종"
                for p in ['퍼펙트', '간편', '굿앤굿', '주력', '종합', '자녀', '나에게맞춘', '참좋은', '훼밀리', '아이러브', '행복플러스']:
                    if p in utterance:
                        prod_name = p
                        break
                calc_res = calculate_nonlife(comp, prod_name, calc_prem, incentive_type="주력", continuous_mode=continuous_mode, requested_week=requested_week)
                return build_kakao_response(calc_res)
                
            # 생명보험: 계층형 질의 유도 및 정밀 S환산 계산
            else:
                candidates = find_candidate_products(comp, utterance)
                
                # 유사 상품이 2개 이상 매칭된 경우 -> 챗봇이 상품 선택 질문 유도!
                if len(candidates) > 1:
                    m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                    t_str = m_term.group(0) if m_term else ""
                    return build_ask_similar_product_response(comp, candidates, calc_prem, term=t_str)

                # 단일 상품 매칭 또는 기본 상품
                prod_group = candidates[0] if candidates else None
                if not prod_group:
                    prod_name = info.get("default_prod", "보장성")
                    suggested_terms = get_suggested_terms_for_life(comp, prod_name)
                    return build_ask_term_response(comp, prod_name, calc_prem, suggested_terms)

                prod_name = clean_prod_short_name(prod_group['full_product'])

                # 1단계: 구분('종') 확인 - 같은 상품인데 구분이 여러 개 있는 경우 질문 유도
                gubun = match_gubun_in_text(prod_group, utterance)
                if gubun is None and len(prod_group['gubuns']) > 1:
                    m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                    t_str = m_term.group(0) if m_term else ""
                    return build_ask_gubun_response(comp, prod_group, calc_prem, term=t_str)

                # 2단계: 납입기간(term) 확인
                term, invalid_term = match_term_in_text(prod_group, utterance)
                if not term:
                    valid_terms = prod_group['terms'] if prod_group['terms'] else ["10년납", "15년납", "20년납"]
                    return build_ask_term_response(comp, prod_name, calc_prem, valid_terms, gubun=gubun or "", invalid_term=invalid_term)

                # 3단계: 법인계약 여부 확인 (한화 하나로 15년, 푸본 원픽 7년, IM 당당한 7년)
                if is_corp_incentive_target(comp, prod_name, term) and not contract_type:
                    return build_ask_contract_type_response(comp, prod_name, calc_prem, term, gubun=gubun or "")

                # 4단계: 모든 조건(상품, 구분/종, 납기, 법인여부) 확정 -> 0.1초 즉시 계산!
                item = match_master_item(prod_group, term, gubun or "")
                s_factor = item['s_factor']
                
                calc_res = calculate_life(
                    company=comp,
                    product_name=f"{prod_name} ({gubun})" if gubun and gubun not in prod_name else prod_name,
                    premium=calc_prem,
                    s_factor=s_factor,
                    term=term,
                    incentive_type="전략",
                    continuous_mode=continuous_mode,
                    contract_type=contract_type or "개인",
                    gubun=gubun or ""
                )
                return build_kakao_response(calc_res)

        # 5. 회사명은 없지만 대표 상품명이 직접 들어온 경우 (전체 생보사 카탈로그 자동 검색)
        if premium is not None:
            all_candidates = []
            for (s, _), p in LIFE_CATALOG.items():
                p_norm = p['norm_name']
                m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                t_raw = m_term.group(0) if m_term else ""
                cleaned = re.sub(r'(\d+[\d,]*)\s*(?:만원|만|원)|계산|시책|얼마|수수료|알려줘|비교|안내|\b\d+\b', ' ', utterance)
                if t_raw: cleaned = cleaned.replace(t_raw, ' ')
                q_norm = normalize_text(cleaned)
                if q_norm and (q_norm in p_norm or p_norm in q_norm):
                    all_candidates.append(p)

            if len(all_candidates) == 1:
                p = all_candidates[0]
                comp = p['company']
                prod_name = clean_prod_short_name(p['full_product'])
                gubun = match_gubun_in_text(p, utterance)
                if gubun is None and len(p['gubuns']) > 1:
                    m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                    t_str = m_term.group(0) if m_term else ""
                    return build_ask_gubun_response(comp, p, premium, term=t_str)
                term, invalid_term = match_term_in_text(p, utterance)
                if not term:
                    valid_terms = p['terms'] if p['terms'] else ["10년납", "15년납", "20년납"]
                    return build_ask_term_response(comp, prod_name, premium, valid_terms, gubun=gubun or "", invalid_term=invalid_term)
                if is_corp_incentive_target(comp, prod_name, term) and not contract_type:
                    return build_ask_contract_type_response(comp, prod_name, premium, term, gubun=gubun or "")
                item = match_master_item(p, term, gubun or "")
                calc_res = calculate_life(comp, prod_name, premium, item['s_factor'], term, "전략", continuous_mode, contract_type=contract_type or "개인", gubun=gubun or "")
                return build_kakao_response(calc_res)
            elif len(all_candidates) > 1:
                m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                t_str = m_term.group(0) if m_term else ""
                first_comp = all_candidates[0]['company']
                return build_ask_similar_product_response(first_comp, all_candidates, premium, term=t_str)
            elif any(k in utterance for k in ['퍼펙트', '간편', '굿앤굿', '주력']):
                m_week = re.search(r'([1-5])\s*주차?', utterance)
                requested_week = f"{m_week.group(1)}주차" if m_week else None
                calc_res = calculate_nonlife("현대해상", "주력보종", premium, "주력", continuous_mode, requested_week=requested_week)
                return build_kakao_response(calc_res)

        # 6. 해석 불가 질문 -> 사용자 지정 표준 폴백 메시지 반환
        return build_fallback_response()

    except Exception as e:
        return build_fallback_response()
