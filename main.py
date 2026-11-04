import urllib.parse
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
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="스카이블루에셋 정산 챗봇", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import json
LIFE_PRODUCTS = json.loads('[{"company": "한화", "product": "제로백H종신", "term": "10년납", "gubun": "일반가입", "s_factor": 1140.0}, {"company": "한화", "product": "제로백H종신", "term": "20년납 이상", "gubun": "", "s_factor": 1425.0}, {"company": "한화", "product": "제로백H종신", "term": "10년납", "gubun": "간편가입", "s_factor": 1092.5}, {"company": "한화", "product": "제로백H종신", "term": "20년납 이상", "gubun": "", "s_factor": 1377.5}, {"company": "한화", "product": "H 종신", "term": "5년납", "gubun": "일반가입", "s_factor": 605.0}, {"company": "한화", "product": "H 종신", "term": "7년납", "gubun": "", "s_factor": 880.0000000000001}, {"company": "한화", "product": "H 종신", "term": "5년납", "gubun": "간편가입", "s_factor": 550.0}, {"company": "한화", "product": "H 종신", "term": "7년납", "gubun": "", "s_factor": 825.0000000000001}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "5년납", "gubun": "일반가입", "s_factor": 605.0}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "7년납", "gubun": "", "s_factor": 880.0000000000001}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "10년납", "gubun": "", "s_factor": 1100.0}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "5년납", "gubun": "간편가입", "s_factor": 550.0}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "7년납", "gubun": "", "s_factor": 825.0000000000001}, {"company": "한화", "product": "밸류플러스보장보험2.0", "term": "10년납", "gubun": "", "s_factor": 1100.0}, {"company": "한화", "product": "건강더한종신", "term": "7년납", "gubun": "일반가입", "s_factor": 880.0000000000001}, {"company": "한화", "product": "건강더한종신", "term": "10년납", "gubun": "", "s_factor": 1100.0}, {"company": "한화", "product": "건강더한종신", "term": "7년납", "gubun": "간편가입", "s_factor": 825.0000000000001}, {"company": "한화", "product": "건강더한종신", "term": "10년납", "gubun": "", "s_factor": 1100.0}, {"company": "한화", "product": "필요할때쓰는종신", "term": "10년납", "gubun": "일반,간편", "s_factor": 1100.0}, {"company": "한화", "product": "필요할때쓰는종신", "term": "12년납", "gubun": "", "s_factor": 1210.0}, {"company": "한화", "product": "(간편)경영인H정기", "term": "전기납", "gubun": "", "s_factor": 1800.0}, {"company": "한화", "product": "상속H종신보험", "term": "10년납", "gubun": "일반가입", "s_factor": 1100.0}, {"company": "한화", "product": "상속H종신보험", "term": "15년납", "gubun": "", "s_factor": 1500.0}, {"company": "한화", "product": "상속H종신보험", "term": "20년납 이상", "gubun": "", "s_factor": 1700.0}, {"company": "한화", "product": "상속H종신보험", "term": "10년납", "gubun": "간편가입", "s_factor": 1000.0}, {"company": "한화", "product": "상속H종신보험", "term": "15년납", "gubun": "", "s_factor": 1400.0}, {"company": "한화", "product": "상속H종신보험", "term": "20년납 이상", "gubun": "", "s_factor": 1600.0}, {"company": "한화", "product": "하나로 H종신", "term": "10년납", "gubun": "일반가입 간편가입", "s_factor": 1000.0}, {"company": "한화", "product": "하나로 H종신", "term": "15년납", "gubun": "", "s_factor": 1300.0}, {"company": "한화", "product": "하나로 H종신", "term": "20년납 이상", "gubun": "", "s_factor": 1500.0}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "s_factor": 846.0}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "10년납", "gubun": "", "s_factor": 1020.0}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "20년납↑", "gubun": "", "s_factor": 1800.0}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "s_factor": 902.4}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "10년납", "gubun": "", "s_factor": 1080.0}, {"company": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "20년납↑", "gubun": "", "s_factor": 1860.0}, {"company": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반심사형 간편심사형", "s_factor": 789.6000000000001}, {"company": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 846.0}, {"company": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 1020.0000000000002}, {"company": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 1380.0}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "5년납", "gubun": "일반", "s_factor": 655.1999999999999}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "7년납", "gubun": "", "s_factor": 856.8}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "10년납", "gubun": "", "s_factor": 1108.8}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "12년납", "gubun": "", "s_factor": 1209.6}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "15년납", "gubun": "", "s_factor": 1461.6}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "20년납↑", "gubun": "", "s_factor": 2100.0}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "5년납", "gubun": "간편", "s_factor": 705.6}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "7년납", "gubun": "", "s_factor": 806.4}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "10년납", "gubun": "", "s_factor": 1209.6}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "12년납", "gubun": "", "s_factor": 1310.3999999999999}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "15년납", "gubun": "", "s_factor": 1512.0}, {"company": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "20년납↑", "gubun": "", "s_factor": 2100.0}, {"company": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반,간편", "s_factor": 806.4}, {"company": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 1159.2}, {"company": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 1562.3999999999999}, {"company": "DB", "product": "(간편한)경영인 정기(2501) (해약환급금 일부지급형)", "term": "1형 (5%체증형)", "gubun": "", "s_factor": 1702.8}, {"company": "DB", "product": "(간편한)경영인 정기(2501) (해약환급금 일부지급형)", "term": "2형 (10%체증형)", "gubun": "", "s_factor": 1702.8}, {"company": "신한", "product": "종신보험 세븐Plus골드", "term": "20년납", "gubun": "일반,간편", "s_factor": 1120.0}, {"company": "신한", "product": "종신보험 세븐PlusⅡ", "term": "20년납", "gubun": "일반,간편", "s_factor": 1400.0}, {"company": "신한", "product": "신한모아더드림종신 (해약환급금 일부지급형)", "term": "5년납이상", "gubun": "일반심사 간편심사", "s_factor": 481.0}, {"company": "신한", "product": "신한모아더드림종신 (해약환급금 일부지급형)", "term": "7년납이상", "gubun": "", "s_factor": 663.0}, {"company": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반심사 간편심사", "s_factor": 420.0}, {"company": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 735.0}, {"company": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 840.0}, {"company": "신한", "product": "(간편가입)종신보험 세븐Plus", "term": "20년납", "gubun": "", "s_factor": 1100.0}, {"company": "신한", "product": "위너스경영인정기 (체증형)", "term": "20년납이상", "gubun": "일반심사형", "s_factor": 1400.0}, {"company": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "5년납", "gubun": "일반심사 간편심사", "s_factor": 450.0}, {"company": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "7년납", "gubun": "", "s_factor": 600.0}, {"company": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "10년납", "gubun": "", "s_factor": 900.0}, {"company": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "15년납", "gubun": "", "s_factor": 1200.0}, {"company": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "20년납", "gubun": "", "s_factor": 1455.0}, {"company": "신한", "product": "The든든한종신보험", "term": "10년납", "gubun": "일반심사 간편심사", "s_factor": 900.0}, {"company": "신한", "product": "The든든한종신보험", "term": "15년납", "gubun": "", "s_factor": 1200.0}, {"company": "신한", "product": "The든든한종신보험", "term": "20년납", "gubun": "", "s_factor": 1455.0}, {"company": "신한", "product": "(간편가입)리필종신", "term": "10년납", "gubun": "기본납입형", "s_factor": 630.0}, {"company": "신한", "product": "(간편가입)리필종신", "term": "20년납", "gubun": "", "s_factor": 840.0}, {"company": "신한", "product": "(간편가입)리필종신", "term": "10년납", "gubun": "집중납입형", "s_factor": 420.0}, {"company": "신한", "product": "(간편가입)리필종신", "term": "20년납", "gubun": "", "s_factor": 570.0}, {"company": "신한", "product": "3케어리워드종신", "term": "10년납", "gubun": "일반,간편", "s_factor": 630.0}, {"company": "신한", "product": "3케어리워드종신", "term": "20년납", "gubun": "", "s_factor": 840.0}, {"company": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "10년납이상", "gubun": "", "s_factor": 675.0}, {"company": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "15년납이상", "gubun": "", "s_factor": 855.0}, {"company": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "20년납이상", "gubun": "", "s_factor": 990.0}, {"company": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)", "term": "10년납", "gubun": "일반심사 간편심사", "s_factor": 720.0}, {"company": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)", "term": "15년납", "gubun": "", "s_factor": 900.0}, {"company": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)", "term": "20년납이상", "gubun": "", "s_factor": 1080.0}, {"company": "신한", "product": "통합건강보험 원(ONE) 갱신형", "term": "10년납이상", "gubun": "일반,간편", "s_factor": 720.0}, {"company": "신한", "product": "통합건강보험 원(ONE) 갱신형", "term": "20년납이상", "gubun": "", "s_factor": 1080.0}, {"company": "신한", "product": "신한ONE더라이프 연금", "term": "5년납이상", "gubun": "연금액 보증형", "s_factor": 50.0}, {"company": "신한", "product": "신한ONE더라이프 연금", "term": "7년납이상", "gubun": "", "s_factor": 250.0}, {"company": "신한", "product": "신한ONE더라이프 연금", "term": "10년납이상", "gubun": "", "s_factor": 550.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "5년납", "gubun": "기본형", "s_factor": 130.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "7년납", "gubun": "", "s_factor": 300.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "10년납이상", "gubun": "", "s_factor": 420.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "5년납", "gubun": "연금 강화형", "s_factor": 170.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "7년납", "gubun": "", "s_factor": 340.0}, {"company": "신한", "product": "신한ONE더드림 변액연금", "term": "10년납이상", "gubun": "", "s_factor": 560.0}, {"company": "KB", "product": "7년의약속 플러스 평생종신", "term": "20년납", "gubun": "-", "s_factor": 786.0}, {"company": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "5년납", "gubun": "", "s_factor": 414.09999999999997}, {"company": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "7년납", "gubun": "", "s_factor": 479.7}, {"company": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "10년납", "gubun": "", "s_factor": 561.6999999999999}, {"company": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "보증비용 부과형", "s_factor": 738.0}, {"company": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 762.5999999999999}, {"company": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 861.0}, {"company": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 889.6999999999999}, {"company": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "20년납 이상", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "경영인 정기보험Ⅲ", "term": "20년납 이상", "gubun": "", "s_factor": 1348.8999999999999}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "5년납", "gubun": "계약자 적립액 보증형", "s_factor": 250.1}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "7년납", "gubun": "", "s_factor": 410.0}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "10년납", "gubun": "", "s_factor": 684.6999999999999}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "5년납", "gubun": "계약자 적립액 미보증형", "s_factor": 164.0}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "7년납", "gubun": "", "s_factor": 225.5}, {"company": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "10년납", "gubun": "", "s_factor": 262.4}, {"company": "KB", "product": "KB넥스트레벨업연금보험", "term": "10년납", "gubun": "보증형", "s_factor": 635.5}, {"company": "KB", "product": "KB넥스트레벨업연금보험", "term": "12년납", "gubun": "", "s_factor": 684.6999999999999}, {"company": "KB", "product": "KB넥스트레벨업연금보험", "term": "10년납", "gubun": "미보증형", "s_factor": 262.4}, {"company": "KB", "product": "KB넥스트레벨업연금보험", "term": "12년납", "gubun": "", "s_factor": 303.4}, {"company": "KB", "product": "100세든든 연금보험(기본형)", "term": "10년납이상", "gubun": "", "s_factor": 402.0}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "10년납", "gubun": "해약환급금 미지급형", "s_factor": 491.99999999999994}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "15년납", "gubun": "", "s_factor": 758.5}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "20년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "30년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "10년납", "gubun": "갱신형", "s_factor": 491.99999999999994}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "20년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "30년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "10년납", "gubun": "해약환급금 미지급형", "s_factor": 491.99999999999994}, {"company": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "15년납", "gubun": "", "s_factor": 758.5}, {"company": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "20년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "30년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "10년납", "gubun": "", "s_factor": 902.0}, {"company": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "15년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "20년납", "gubun": "", "s_factor": 1127.5}, {"company": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "30년납", "gubun": "", "s_factor": 1148.0}, {"company": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "10년납", "gubun": "", "s_factor": 491.99999999999994}, {"company": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "15년납", "gubun": "", "s_factor": 758.5}, {"company": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "20년납", "gubun": "", "s_factor": 1025.0}, {"company": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "30년납", "gubun": "", "s_factor": 1025.0}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "20년납", "gubun": "일반가입", "s_factor": 1391.8500000000001}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "15년납", "gubun": "", "s_factor": 1246.05}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "10년납", "gubun": "", "s_factor": 647.5500000000001}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "7년납", "gubun": "", "s_factor": 540.9}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "5년납", "gubun": "", "s_factor": 305.1}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "20년납", "gubun": "간편가입", "s_factor": 1156.05}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "15년납", "gubun": "", "s_factor": 1156.05}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "10년납", "gubun": "", "s_factor": 497.7}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "7년납", "gubun": "", "s_factor": 540.9}, {"company": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "5년납", "gubun": "", "s_factor": 266.40000000000003}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "20년납", "gubun": "일반가입", "s_factor": 1391.8500000000001}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "15년납", "gubun": "", "s_factor": 1246.05}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "10년납", "gubun": "", "s_factor": 647.5500000000001}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "7년납", "gubun": "", "s_factor": 459.0}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "5년납", "gubun": "", "s_factor": 227.70000000000002}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "20년납", "gubun": "간편가입", "s_factor": 1117.8}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "15년납", "gubun": "", "s_factor": 1117.8}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "10년납", "gubun": "", "s_factor": 459.0}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "7년납", "gubun": "", "s_factor": 305.1}, {"company": "메트", "product": "백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "5년납", "gubun": "", "s_factor": 189.45000000000002}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "25년납이상", "gubun": "3천만 이상", "s_factor": 1775.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "20년납이상", "gubun": "", "s_factor": 1775.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "15년납이상", "gubun": "", "s_factor": 1775.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "10년납이상", "gubun": "", "s_factor": 1435.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "9년납이하", "gubun": "", "s_factor": 1191.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "7년납이하", "gubun": "", "s_factor": 915.5}, {"company": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "5년납이하", "gubun": "", "s_factor": 764.5}, {"company": "메트", "product": "360 종합보장보험", "term": "20년납이상", "gubun": "일반가입 간편가입", "s_factor": 1597.95}, {"company": "메트", "product": "360 종합보장보험", "term": "19년납이하", "gubun": "", "s_factor": 1541.7}, {"company": "메트", "product": "360 종합보장보험", "term": "14년납이하", "gubun": "", "s_factor": 1156.05}, {"company": "메트", "product": "360 암보험 (갱신형)", "term": "전기납", "gubun": "일반가입", "s_factor": 1597.95}, {"company": "메트", "product": "간편 360 종합보장보험 (갱신형)", "term": "전기납", "gubun": "간편가입", "s_factor": 1442.7}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "5년", "gubun": "해지환급금 일부지급형", "s_factor": 510.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "7년", "gubun": "", "s_factor": 810.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "10년", "gubun": "", "s_factor": 990.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "12년", "gubun": "", "s_factor": 1080.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "5년", "gubun": "표준형", "s_factor": 390.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "7년", "gubun": "", "s_factor": 540.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "10년", "gubun": "", "s_factor": 750.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "12년", "gubun": "", "s_factor": 870.0}, {"company": "농협", "product": "마이초이스NH종신보험", "term": "20년", "gubun": "", "s_factor": 1440.0}, {"company": "농협", "product": "투스텝NH종신", "term": "10년", "gubun": "해약환급금일부지급형", "s_factor": 480.0}, {"company": "농협", "product": "투스텝NH종신", "term": "12년", "gubun": "", "s_factor": 630.0}, {"company": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "10년", "gubun": "스마트 페이형", "s_factor": 450.0}, {"company": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "15년", "gubun": "", "s_factor": 720.0}, {"company": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "10년", "gubun": "일반페이형", "s_factor": 690.0}, {"company": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "15년", "gubun": "", "s_factor": 1020.0}, {"company": "농협", "product": "스텝업700NH종신보험", "term": "해약환급금일부지급형", "gubun": "", "s_factor": 1397.5}, {"company": "농협", "product": "행복한NH경영인정기", "term": "해약환급금일부지급형", "gubun": "", "s_factor": 1350.0}, {"company": "농협", "product": "행복한NH경영인정기", "term": "표준형", "gubun": "", "s_factor": 625.0}, {"company": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "10년이상", "gubun": "해약환급금 일부지급형", "s_factor": 550.0}, {"company": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "15년이상", "gubun": "", "s_factor": 775.0}, {"company": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "20년이상", "gubun": "", "s_factor": 975.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "10년이상", "gubun": "해약환급금 미지급형", "s_factor": 450.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "15년이상", "gubun": "", "s_factor": 650.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "20년이상", "gubun": "", "s_factor": 850.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "30년이상", "gubun": "", "s_factor": 1100.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "10년이상", "gubun": "표준형", "s_factor": 400.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "15년이상", "gubun": "", "s_factor": 525.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "20년이상", "gubun": "", "s_factor": 650.0}, {"company": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "30년이상", "gubun": "", "s_factor": 875.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "10년미만", "gubun": "간편가입", "s_factor": 250.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "10년이상", "gubun": "", "s_factor": 450.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "15년이상", "gubun": "", "s_factor": 650.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "20년이상", "gubun": "", "s_factor": 800.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "10년미만", "gubun": "일반가입", "s_factor": 225.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "10년이상", "gubun": "", "s_factor": 425.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "15년이상", "gubun": "", "s_factor": 600.0}, {"company": "농협", "product": "핑크케어 NH건강보험", "term": "20년이상", "gubun": "", "s_factor": 750.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "10년이상", "gubun": "해지환급금 미지급형", "s_factor": 475.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "15년이상", "gubun": "", "s_factor": 650.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "20년이상", "gubun": "", "s_factor": 775.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "10년이상", "gubun": "표준형", "s_factor": 375.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "15년이상", "gubun": "", "s_factor": 500.0}, {"company": "농협", "product": "건강플러스NH통합보험", "term": "20년이상", "gubun": "", "s_factor": 625.0}, {"company": "농협", "product": "치료비안심해2NH건강보험", "term": "10년미만", "gubun": "", "s_factor": 275.0}, {"company": "농협", "product": "치료비안심해2NH건강보험", "term": "10년이상", "gubun": "", "s_factor": 525.0}, {"company": "농협", "product": "치료비안심해2NH건강보험", "term": "15년이상", "gubun": "", "s_factor": 725.0}, {"company": "농협", "product": "치료비안심해2NH건강보험", "term": "20년이상", "gubun": "", "s_factor": 900.0}, {"company": "농협", "product": "치료비안심해2NH건강보험", "term": "갱신형", "gubun": "", "s_factor": 1000.0}, {"company": "동양", "product": "우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)", "term": "5년납", "gubun": "보장형_평준납입형", "s_factor": 385.0}, {"company": "동양", "product": "우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)", "term": "7년납", "gubun": "", "s_factor": 454.99999999999994}, {"company": "동양", "product": "우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)", "term": "10년납", "gubun": "", "s_factor": 840.0}, {"company": "동양", "product": "우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)", "term": "10년납", "gubun": "보장형_체감납입형", "s_factor": 350.0}, {"company": "동양", "product": "우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)", "term": "10년납", "gubun": "표준형", "s_factor": 140.0}, {"company": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "10년납", "gubun": "건강체 표준체", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "15년납", "gubun": "", "s_factor": 1435.0}, {"company": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "20년납", "gubun": "", "s_factor": 1715.0}, {"company": "동양", "product": "우리WON하는5배더행복한플러스종신", "term": "15년납", "gubun": "일반/간편", "s_factor": 499.5}, {"company": "동양", "product": "우리WON하는7배더행복한플러스종신", "term": "20년납", "gubun": "일반/간편", "s_factor": 536.5}, {"company": "동양", "product": "우리WON안심상속종신", "term": "10년납", "gubun": "일반/간편", "s_factor": 595.0}, {"company": "동양", "product": "우리WON안심상속종신", "term": "15년납", "gubun": "", "s_factor": 805.0}, {"company": "동양", "product": "우리WON안심상속종신", "term": "20년납 이상", "gubun": "", "s_factor": 1155.0}, {"company": "동양", "product": "우리WON하는건강플러스종신", "term": "10년납", "gubun": "해약환급금일부지급형", "s_factor": 525.0}, {"company": "동양", "product": "우리WON하는치매간병(주계약), 우리WON하는 건강한보장", "term": "10년납이상", "gubun": "해약환급금일부/미지급형 표준형", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는치매간병(주계약), 우리WON하는 건강한보장", "term": "20년납이상", "gubun": "", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는 보장", "term": "10년납", "gubun": "일반", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는 보장", "term": "20년납 이상", "gubun": "", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는 보장", "term": "10년납 이상", "gubun": "간편", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는 보장", "term": "20년납이상", "gubun": "", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는보장(갱신형)", "term": "20년납, 30년납", "gubun": "일반/간편", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는암 (해약환급금 일부지급형, 표준형)", "term": "10년납", "gubun": "일반/간편", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는암 (해약환급금 일부지급형, 표준형)", "term": "20년납 이상", "gubun": "", "s_factor": 1085.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "종합설계형", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "종합설계형_ 출생후보장기간", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "3대질환보장형", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "3대질환보장형_ 출생후보장기간", "s_factor": 420.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "", "s_factor": 735.0}, {"company": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "", "s_factor": 735.0}, {"company": "흥국", "product": "미리받는트리플더블업건강종신", "term": "20년납이상", "gubun": "", "s_factor": 800.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "20년↑", "gubun": "라이프 밸런스형", "s_factor": 800.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "15년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑(일반)", "gubun": "", "s_factor": 440.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑(간편)", "gubun": "", "s_factor": 400.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "20년↑", "gubun": "프리미엄 보장형", "s_factor": 800.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "15년↑", "gubun": "", "s_factor": 560.0}, {"company": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑", "gubun": "", "s_factor": 280.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "20년↑", "gubun": "라이프 밸런스형", "s_factor": 800.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "15년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "10년↑", "gubun": "", "s_factor": 480.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "20년↑", "gubun": "프리미엄 보장형", "s_factor": 800.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "15년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "10년↑", "gubun": "", "s_factor": 320.0}, {"company": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "해약환급금 미지급형", "s_factor": 1100.0}, {"company": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "", "s_factor": 797.5000000000001}, {"company": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "", "s_factor": 522.5}, {"company": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "해약환급금 일부지급형", "s_factor": 935.0000000000001}, {"company": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "", "s_factor": 715.0000000000001}, {"company": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "", "s_factor": 440.00000000000006}, {"company": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "표준형", "s_factor": 797.5000000000001}, {"company": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "", "s_factor": 605.0}, {"company": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "", "s_factor": 385.00000000000006}, {"company": "흥국", "product": "치매담은Plus보장보험", "term": "15년↑", "gubun": "해약환급금 일부지급형", "s_factor": 715.0000000000001}, {"company": "흥국", "product": "치매담은Plus보장보험", "term": "10년↑", "gubun": "", "s_factor": 440.00000000000006}, {"company": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "해약환급금 미지급형", "s_factor": 1100.0}, {"company": "흥국", "product": "다(多)사랑통합", "term": "15년↑", "gubun": "", "s_factor": 715.0000000000001}, {"company": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "", "s_factor": 330.0}, {"company": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "표준형", "s_factor": 935.0000000000001}, {"company": "흥국", "product": "다(多)사랑통합", "term": "15년↑", "gubun": "", "s_factor": 715.0000000000001}, {"company": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "", "s_factor": 330.0}, {"company": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "갱신형", "s_factor": 1100.0}, {"company": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "20년↑", "gubun": "해약환급금 미지급형", "s_factor": 1100.0}, {"company": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "15년↑", "gubun": "", "s_factor": 715.0000000000001}, {"company": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "10년↑", "gubun": "", "s_factor": 330.0}, {"company": "흥국", "product": "오튼튼5.10.5건강보험(갱신형)", "term": "20년↑", "gubun": "갱신형", "s_factor": 1100.0}, {"company": "흥국", "product": "다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험", "term": "20년↑", "gubun": "해약환급금 미지급형", "s_factor": 1100.0}, {"company": "흥국", "product": "다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험", "term": "10년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "3.1.1간편건강보험(갱신형)", "term": "20년↑", "gubun": "갱신형", "s_factor": 1100.0}, {"company": "흥국", "product": "다사랑3N5간편건강", "term": "20년↑", "gubun": "해약환급금 미지급형", "s_factor": 1100.0}, {"company": "흥국", "product": "다사랑3N5간편건강", "term": "10년↑", "gubun": "", "s_factor": 660.0}, {"company": "흥국", "product": "다사랑3N5간편건강", "term": "20년↑", "gubun": "표준형", "s_factor": 1100.0}, {"company": "흥국", "product": "다사랑3N5간편건강", "term": "10년↑", "gubun": "", "s_factor": 550.0}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "20년납", "gubun": "해지환급금 미지급형", "s_factor": 1430.0000000000002}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "15년납", "gubun": "", "s_factor": 1309.0}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "12년납", "gubun": "", "s_factor": 1045.0}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "10년납", "gubun": "", "s_factor": 742.5000000000001}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "20년납", "gubun": "기본형", "s_factor": 357.50000000000006}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "15년납", "gubun": "", "s_factor": 330.0}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "12년납", "gubun": "", "s_factor": 302.5}, {"company": "라이나", "product": "THE건강해지는 종신", "term": "10년납", "gubun": "", "s_factor": 275.0}, {"company": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "20년납", "gubun": "해약환급금 일부지급형", "s_factor": 630.0}, {"company": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "15년납", "gubun": "", "s_factor": 570.0}, {"company": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "10년납", "gubun": "", "s_factor": 510.0}, {"company": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "7년납", "gubun": "", "s_factor": 390.0}, {"company": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "15년납이상", "gubun": "해지환급금 미지급형", "s_factor": 1430.0000000000002}, {"company": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "10년납", "gubun": "", "s_factor": 907.5000000000001}, {"company": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "15년납이상", "gubun": "기본형", "s_factor": 275.0}, {"company": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "10년납", "gubun": "", "s_factor": 192.50000000000003}, {"company": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "20년납이상", "gubun": "주계약", "s_factor": 1102.5}, {"company": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "15년납", "gubun": "", "s_factor": 990.0}, {"company": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "10년납", "gubun": "", "s_factor": 720.0}, {"company": "라이나", "product": "암으로치료하였어도 OK암", "term": "-", "gubun": "", "s_factor": 900.0}, {"company": "라이나", "product": "THE실속있는치아, THE건강한치아V THE든든해진라이나치아", "term": "10년만기", "gubun": "갱신형", "s_factor": 1102.5}, {"company": "라이나", "product": "THE실속있는치아, THE건강한치아V THE든든해진라이나치아", "term": "5년만기", "gubun": "", "s_factor": 630.0}, {"company": "라이나", "product": "THE건강한치아보험V(리셋형)", "term": "갱신형", "gubun": "", "s_factor": 1102.5}, {"company": "라이나", "product": "골라담는(간편)건강보험 (갱신형)", "term": "20년납", "gubun": "주계약", "s_factor": 1102.5}, {"company": "라이나", "product": "골라담는(간편)건강보험 (갱신형)", "term": "10년납", "gubun": "", "s_factor": 684.0}, {"company": "라이나", "product": "새로담는 (간편)건강보험(클래식)", "term": "해약환급금미지급형Ⅱ", "gubun": "", "s_factor": 1102.5}, {"company": "라이나", "product": "새로담는 (간편)건강보험(클래식)", "term": "기본형", "gubun": "", "s_factor": 900.0}, {"company": "라이나", "product": "새로담는 간편건강보험(갱신형)", "term": "20년납", "gubun": "해약환급금 미지급형", "s_factor": 1102.5}, {"company": "라이나", "product": "새로담는 간편건강보험(갱신형)", "term": "10년납", "gubun": "", "s_factor": 684.0}, {"company": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "해약환급금미지급형Ⅱ", "gubun": "", "s_factor": 1102.5}, {"company": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "", "gubun": "", "s_factor": 1102.5}, {"company": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "", "gubun": "", "s_factor": 1102.5}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10년미만", "gubun": "저해약", "s_factor": 360.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10-14년", "gubun": "", "s_factor": 880.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "15-19년", "gubun": "", "s_factor": 1160.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "20년납이상", "gubun": "", "s_factor": 1280.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10년미만", "gubun": "일반형", "s_factor": 280.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10-14년", "gubun": "", "s_factor": 480.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "15-19년", "gubun": "", "s_factor": 640.0}, {"company": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "20년납이상", "gubun": "", "s_factor": 800.0}, {"company": "교보", "product": "교보(간편)K-실속종신보험", "term": "5~6년", "gubun": "-", "s_factor": 500.5}, {"company": "교보", "product": "교보(간편)K-실속종신보험", "term": "7~9년", "gubun": "-", "s_factor": 819.0}, {"company": "교보", "product": "교보(간편)K-실속종신보험", "term": "10~14년", "gubun": "-", "s_factor": 1183.0}, {"company": "교보", "product": "교보(간편)K-실속종신보험", "term": "15년", "gubun": "-", "s_factor": 1319.5}, {"company": "교보", "product": "교보(간편)모두지킴종신", "term": "10년납 미만", "gubun": "", "s_factor": 630.0}, {"company": "교보", "product": "교보(간편)모두지킴종신", "term": "10년납-14년납", "gubun": "", "s_factor": 909.9999999999999}, {"company": "교보", "product": "교보(간편)모두지킴종신", "term": "15년납-19년납", "gubun": "", "s_factor": 1014.9999999999999}, {"company": "교보", "product": "교보(간편)모두지킴종신", "term": "20년납이상", "gubun": "", "s_factor": 1120.0}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "10년납 미만", "gubun": "일반가입", "s_factor": 489.99999999999994}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "10년납-14년납", "gubun": "", "s_factor": 979.9999999999999}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "15년납-19년납", "gubun": "", "s_factor": 1085.0}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "20년납 이상", "gubun": "", "s_factor": 1260.0}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "10년납 미만", "gubun": "간편가입", "s_factor": 454.99999999999994}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "10년납-14년납", "gubun": "", "s_factor": 944.9999999999999}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "15년납-19년납", "gubun": "", "s_factor": 1050.0}, {"company": "교보", "product": "교보다시채움건강종신보험", "term": "20년납 이상", "gubun": "", "s_factor": 1225.0}, {"company": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "5년납~6년납", "gubun": "", "s_factor": 489.99999999999994}, {"company": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "7년납~9년납", "gubun": "", "s_factor": 630.0}, {"company": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "10년납~14년납", "gubun": "", "s_factor": 979.9999999999999}, {"company": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "15년납~19년납", "gubun": "", "s_factor": 1085.0}, {"company": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "20년납 이상", "gubun": "", "s_factor": 1155.0}, {"company": "교보", "product": "교보(간편)밸런스건강보험", "term": "10년납-14년납", "gubun": "", "s_factor": 700.0}, {"company": "교보", "product": "교보(간편)밸런스건강보험", "term": "15년납-19년납", "gubun": "", "s_factor": 979.9999999999999}, {"company": "교보", "product": "교보(간편)밸런스건강보험", "term": "20년납이상", "gubun": "", "s_factor": 1225.0}, {"company": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "10년미만", "gubun": "-", "s_factor": 525.0}, {"company": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "10년", "gubun": "-", "s_factor": 979.9999999999999}, {"company": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "12년", "gubun": "", "s_factor": 979.9999999999999}, {"company": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "15-19년", "gubun": "", "s_factor": 1155.0}, {"company": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "20년납이상", "gubun": "-", "s_factor": 1400.0}, {"company": "교보", "product": "K-밸류업종신 (베이직,프라임형)", "term": "-", "gubun": "일반,간편", "s_factor": 1425.0}, {"company": "교보", "product": "K-밸류업종신 (라이트형)", "term": "66세미만", "gubun": "일반", "s_factor": 1425.0}, {"company": "교보", "product": "K-밸류업종신 (라이트형)", "term": "66세이상", "gubun": "", "s_factor": 1140.0}, {"company": "교보", "product": "K-밸류업종신 (라이트형)", "term": "61세미만", "gubun": "간편", "s_factor": 1425.0}, {"company": "교보", "product": "K-밸류업종신 (라이트형)", "term": "61세이상", "gubun": "", "s_factor": 1140.0}, {"company": "교보", "product": "교보경영인정기(보증비용부과형)", "term": "20년납이상", "gubun": "일반,간편", "s_factor": 1350.0}, {"company": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "10년 미만", "gubun": "", "s_factor": 425.0}, {"company": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "10년-14년", "gubun": "", "s_factor": 765.0}, {"company": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "15년-19년", "gubun": "", "s_factor": 1105.0}, {"company": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "20년 이상", "gubun": "", "s_factor": 1360.0}, {"company": "KDB", "product": "더블찬스종신Ⅱ", "term": "5년납", "gubun": "", "s_factor": 495.0}, {"company": "KDB", "product": "더블찬스종신Ⅱ", "term": "7년납", "gubun": "", "s_factor": 675.0}, {"company": "KDB", "product": "더블찬스종신Ⅱ", "term": "10년납", "gubun": "", "s_factor": 945.0}, {"company": "KDB", "product": "트리플찬스 종신", "term": "10년납", "gubun": "", "s_factor": 900.0}, {"company": "KDB", "product": "트리플찬스 종신", "term": "15년납", "gubun": "", "s_factor": 1080.0}, {"company": "KDB", "product": "트리플찬스 종신", "term": "20년납", "gubun": "", "s_factor": 1350.0}, {"company": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "5년납", "gubun": "체증형", "s_factor": 450.0}, {"company": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "7년납", "gubun": "", "s_factor": 630.0}, {"company": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "10년납", "gubun": "", "s_factor": 900.0}, {"company": "KDB", "product": "서포트100건강종신", "term": "10년납", "gubun": "", "s_factor": 900.0}, {"company": "KDB", "product": "서포트100건강종신", "term": "15년납", "gubun": "", "s_factor": 1080.0}, {"company": "KDB", "product": "서포트100건강종신", "term": "20년납이상", "gubun": "", "s_factor": 1350.0}, {"company": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "5년납", "gubun": "", "s_factor": 300.0}, {"company": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "7년납", "gubun": "", "s_factor": 420.0}, {"company": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "10년납", "gubun": "", "s_factor": 720.0}, {"company": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "15년납", "gubun": "", "s_factor": 840.0}, {"company": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "20년납이상", "gubun": "", "s_factor": 1020.0}, {"company": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "10년납", "gubun": "", "s_factor": 720.0}, {"company": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "15년납", "gubun": "", "s_factor": 840.0}, {"company": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "20년납 이상", "gubun": "", "s_factor": 1020.0}, {"company": "KDB", "product": "버팀목 치매보장", "term": "10년납", "gubun": "", "s_factor": 720.0}, {"company": "KDB", "product": "버팀목 치매보장", "term": "15년납", "gubun": "", "s_factor": 840.0}, {"company": "KDB", "product": "버팀목 치매보장", "term": "20년납 이상", "gubun": "", "s_factor": 1020.0}, {"company": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "5년납", "gubun": "", "s_factor": 135.0}, {"company": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "7년납", "gubun": "", "s_factor": 360.0}, {"company": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "10년납이상", "gubun": "", "s_factor": 630.0}, {"company": "KDB", "product": "더!행복플러스종신", "term": "10년납", "gubun": "", "s_factor": 854.0}, {"company": "KDB", "product": "더!행복플러스종신", "term": "20년납", "gubun": "", "s_factor": 1098.0}, {"company": "KDB", "product": "더!행복세븐종신", "term": "20년납", "gubun": "", "s_factor": 1403.0}, {"company": "ABL", "product": "우리WON세븐종신보험", "term": "20년납", "gubun": "일반/간편", "s_factor": 1113.0}, {"company": "ABL", "product": "우리WON더채움종신보험 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반/간편", "s_factor": 756.0}, {"company": "ABL", "product": "우리WON더채움종신보험 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 840.0}, {"company": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "s_factor": 672.0}, {"company": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 986.9999999999999}, {"company": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 1260.0}, {"company": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 1407.0}, {"company": "ABL", "product": "우리WON스테이블종신", "term": "7년납", "gubun": "일반심사형 간편심사형", "s_factor": 672.0}, {"company": "ABL", "product": "우리WON스테이블종신", "term": "10년납", "gubun": "", "s_factor": 756.0}, {"company": "ABL", "product": "우리WON스테이블종신", "term": "15년납", "gubun": "", "s_factor": 798.0}, {"company": "ABL", "product": "우리WON스테이블종신", "term": "20년납", "gubun": "", "s_factor": 840.0}, {"company": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "5년납", "gubun": "일반심사형 간편심사형", "s_factor": 588.0}, {"company": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "7년납", "gubun": "", "s_factor": 798.0}, {"company": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "10년납", "gubun": "", "s_factor": 965.9999999999999}, {"company": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "15년납", "gubun": "", "s_factor": 1260.0}, {"company": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "20년납", "gubun": "", "s_factor": 1260.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "5년납", "gubun": "평준형 (일반심사형) (간편심사형)", "s_factor": 630.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 609.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 1029.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 1365.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "20년이상", "gubun": "", "s_factor": 1428.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "5년납", "gubun": "체증형 (일반심사형) (간편심사형)", "s_factor": 588.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 609.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "10년납", "gubun": "", "s_factor": 923.9999999999999}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 1239.0}, {"company": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "20년이상", "gubun": "", "s_factor": 1386.0}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "5년납", "gubun": "해약환급금 미지급형", "s_factor": 378.0}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "10년납", "gubun": "", "s_factor": 672.0}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "15년납", "gubun": "", "s_factor": 965.9999999999999}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "20년납 이상", "gubun": "", "s_factor": 1134.0}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "5년납", "gubun": "기본형", "s_factor": 125.99999999999999}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "10년납", "gubun": "", "s_factor": 482.99999999999994}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "15년납", "gubun": "", "s_factor": 735.0}, {"company": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "20년납 이상", "gubun": "", "s_factor": 944.9999999999999}, {"company": "ABL", "product": "우리WON건강N더보장 종합건강보험", "term": "10년 만기", "gubun": "갱신형", "s_factor": 672.0}, {"company": "ABL", "product": "우리WON건강N더보장 종합건강보험", "term": "20년&30년", "gubun": "", "s_factor": 1134.0}, {"company": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "10년납", "gubun": "일반심사형 간편심사형", "s_factor": 399.0}, {"company": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "15년납", "gubun": "", "s_factor": 882.0}, {"company": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "20년납이상", "gubun": "", "s_factor": 1092.0}, {"company": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "5년납", "gubun": "기본형", "s_factor": 125.99999999999999}, {"company": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "10년납", "gubun": "", "s_factor": 482.99999999999994}, {"company": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "15년납", "gubun": "", "s_factor": 735.0}, {"company": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "20년이상", "gubun": "", "s_factor": 944.9999999999999}, {"company": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "3년납이상", "gubun": "보종코드: 21218", "s_factor": 16.0}, {"company": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "5년납이상", "gubun": "", "s_factor": 200.0}, {"company": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "7년납이상", "gubun": "", "s_factor": 312.0}, {"company": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "10년납이상", "gubun": "", "s_factor": 440.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "5년납이상", "gubun": "일반가입형, 간편고지형", "s_factor": 440.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "7년납이상", "gubun": "", "s_factor": 560.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "10년납이상", "gubun": "", "s_factor": 760.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "12년납이상", "gubun": "", "s_factor": 840.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "15년납이상", "gubun": "", "s_factor": 1160.0}, {"company": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "20년납이상", "gubun": "", "s_factor": 1320.0}, {"company": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "15년납이상", "gubun": "일반가입형, 간편고지형", "s_factor": 1160.0}, {"company": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "20년납이상", "gubun": "", "s_factor": 1320.0}, {"company": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "25년납이상", "gubun": "", "s_factor": 1400.0}, {"company": "미래", "product": "암 걱정없는 암치료보험", "term": "10년납이상", "gubun": "갱신형", "s_factor": 550.0}, {"company": "미래", "product": "암 걱정없는 암치료보험", "term": "20년납이상", "gubun": "", "s_factor": 825.0000000000001}, {"company": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "10년납이상", "gubun": "일반가입형, 간편가입형", "s_factor": 550.0}, {"company": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "15년납이상", "gubun": "", "s_factor": 632.5}, {"company": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "20년납이상", "gubun": "", "s_factor": 715.0000000000001}, {"company": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "10년납이상", "gubun": "기본형, 해약환급금이없는유형", "s_factor": 412.50000000000006}, {"company": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "15년납이상", "gubun": "", "s_factor": 616.0}, {"company": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "20년납이상", "gubun": "", "s_factor": 825.0000000000001}, {"company": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "10년납이상", "gubun": "기본형, 해약환급금이없는유형", "s_factor": 412.50000000000006}, {"company": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "15년납이상", "gubun": "", "s_factor": 616.0}, {"company": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "20년납이상", "gubun": "", "s_factor": 825.0000000000001}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "10년납이상", "gubun": "기본형", "s_factor": 165.0}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "15년납이상", "gubun": "", "s_factor": 203.50000000000003}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "20년납이상", "gubun": "", "s_factor": 247.50000000000003}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "25년납이상", "gubun": "", "s_factor": 286.0}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "10년납이상", "gubun": "해약환급금이없는유형", "s_factor": 412.50000000000006}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "15년납이상", "gubun": "", "s_factor": 616.0}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "20년납이상", "gubun": "", "s_factor": 825.0000000000001}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)", "term": "10년납이상", "gubun": "갱신형", "s_factor": 412.50000000000006}, {"company": "미래", "product": "M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)", "term": "20년납이상", "gubun": "", "s_factor": 825.0000000000001}, {"company": "하나", "product": "하나로 THE연결된 종신", "term": "5년납", "gubun": "일반심사형 간편심사형", "s_factor": 363.00000000000006}, {"company": "하나", "product": "하나로 THE연결된 종신", "term": "7년납", "gubun": "", "s_factor": 473.00000000000006}, {"company": "하나", "product": "하나로 THE연결된 종신", "term": "10년납", "gubun": "", "s_factor": 550.0}, {"company": "하나", "product": "하나로 THE연결된 종신", "term": "15년/20년납", "gubun": "", "s_factor": 990.0000000000001}, {"company": "하나", "product": "하나원!투!종신", "term": "5년납", "gubun": "일반심사형 간편심사형", "s_factor": 308.0}, {"company": "하나", "product": "하나원!투!종신", "term": "7년납", "gubun": "", "s_factor": 330.0}, {"company": "하나", "product": "하나원!투!종신", "term": "10년납", "gubun": "", "s_factor": 418.00000000000006}, {"company": "하나", "product": "CEO경영인정기보험 (전기납)", "term": "해약환급금 일부지급형", "gubun": "", "s_factor": 1440.0}, {"company": "하나", "product": "CEO경영인정기보험 (전기납)", "term": "일반형", "gubun": "", "s_factor": 800.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "10년납", "gubun": "해약환급금 미지급형", "s_factor": 640.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "15년납", "gubun": "", "s_factor": 720.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "20년납", "gubun": "", "s_factor": 880.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "10년납", "gubun": "해약환급금 일부지급형", "s_factor": 480.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "15년납", "gubun": "", "s_factor": 640.0}, {"company": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "20년납", "gubun": "", "s_factor": 760.0}, {"company": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "10년납", "gubun": "해약환급금 미지급형/갱신형", "s_factor": 520.0}, {"company": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "20년/30년납", "gubun": "", "s_factor": 880.0}, {"company": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "10년납", "gubun": "일반형", "s_factor": 360.0}, {"company": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "20년/30년납", "gubun": "", "s_factor": 680.0}, {"company": "하나", "product": "THE든든한연금", "term": "전기납", "gubun": "일반/간편", "s_factor": 605.0}, {"company": "하나", "product": "하나뿐인 변액연금", "term": "5년납", "gubun": "적립형", "s_factor": 220.00000000000003}, {"company": "하나", "product": "하나뿐인 변액연금", "term": "7년납", "gubun": "", "s_factor": 440.00000000000006}, {"company": "하나", "product": "하나뿐인 변액연금", "term": "10년납 이상", "gubun": "", "s_factor": 715.0000000000001}, {"company": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반가입 간편가입", "s_factor": 330.0}, {"company": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "7년납", "gubun": "", "s_factor": 880.0}, {"company": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 1600.0}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "10년", "s_factor": 330.0}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "11~20년", "s_factor": 550.0}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납", "gubun": "", "s_factor": 770.0000000000001}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "21~30년", "s_factor": 550.0}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납이상", "gubun": "", "s_factor": 990.0000000000001}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "31년이상", "s_factor": 440.00000000000006}, {"company": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납이상", "gubun": "", "s_factor": 880.0000000000001}, {"company": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "55세미만", "gubun": "일반가입", "s_factor": 1419.0000000000002}, {"company": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "55세이상", "gubun": "", "s_factor": 1320.0}, {"company": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "-", "gubun": "간편가입", "s_factor": 1419.0000000000002}, {"company": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "10년납", "gubun": "주계약", "s_factor": 250.0}, {"company": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "15년납", "gubun": "", "s_factor": 330.0}, {"company": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "20년납", "gubun": "", "s_factor": 425.0}, {"company": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "30년납", "gubun": "", "s_factor": 425.0}, {"company": "푸본현대", "product": "MAX 연금다운\xa0연금보험", "term": "10년납", "gubun": "1형 보증비용부과형", "s_factor": 546.0}, {"company": "푸본현대", "product": "MAX 연금다운\xa0연금보험", "term": "20년납", "gubun": "", "s_factor": 611.0}, {"company": "푸본현대", "product": "MAX 연금다운\xa0연금보험", "term": "10년납", "gubun": "2형 보증비용미부과형", "s_factor": 130.0}, {"company": "푸본현대", "product": "MAX 연금다운\xa0연금보험", "term": "20년납", "gubun": "", "s_factor": 162.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "5년", "gubun": "1형 연금액강화형", "s_factor": 162.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "7년", "gubun": "", "s_factor": 227.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "10년", "gubun": "", "s_factor": 357.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "5년", "gubun": "2형 일반연금형", "s_factor": 32.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "7년", "gubun": "", "s_factor": 97.5}, {"company": "푸본현대", "product": "MAX UP\xa0연금보험", "term": "10년", "gubun": "", "s_factor": 130.0}, {"company": "IM", "product": "당당한 인생종신 (체증형)", "term": "5년납", "gubun": "일반", "s_factor": 556.8000000000001}, {"company": "IM", "product": "당당한 인생종신 (체증형)", "term": "7년납", "gubun": "", "s_factor": 873.2}, {"company": "IM", "product": "당당한 인생종신 (체증형)", "term": "5년납", "gubun": "간편", "s_factor": 544.0}, {"company": "IM", "product": "당당한 인생종신 (체증형)", "term": "7년납", "gubun": "", "s_factor": 858.4}, {"company": "IM", "product": "더(THE) 행복한 종신보험", "term": "20년이상", "gubun": "", "s_factor": 666.0}, {"company": "IM", "product": "iM Plus세븐UP종신보험", "term": "20년", "gubun": "일반,간편", "s_factor": 932.4}, {"company": "IM", "product": "iM Plus세븐UP골드종신보험", "term": "20년", "gubun": "일반,간편", "s_factor": 1346.8}, {"company": "IM", "product": "iM 트래블PRO변액연금", "term": "5년납", "gubun": "", "s_factor": 229.4}, {"company": "IM", "product": "iM 트래블PRO변액연금", "term": "7년납", "gubun": "", "s_factor": 414.4}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "10년/12년", "gubun": "보험료 10만원이상", "s_factor": 140.6}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "15년/20년이상", "gubun": "", "s_factor": 236.8}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "10이상", "gubun": "보험료 20만원이상", "s_factor": 577.2}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "12년이상", "gubun": "", "s_factor": 606.8}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "15년/20년이상", "gubun": "", "s_factor": 651.2}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "5년이상", "gubun": "보험료 30만원이상", "s_factor": 214.6}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "7년이상", "gubun": "", "s_factor": 370.0}, {"company": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "5년이상", "gubun": "50만원 이상", "s_factor": 244.2}, {"company": "IM", "product": "든든한 인생치매 (주계약기준)", "term": "5년납", "gubun": "", "s_factor": 569.8}, {"company": "IM", "product": "든든한 인생치매 (주계약기준)", "term": "7년납", "gubun": "", "s_factor": 799.2}, {"company": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "10년", "gubun": "1종,2종", "s_factor": 414.4}, {"company": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "15년", "gubun": "", "s_factor": 614.2}, {"company": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "20년이상", "gubun": "", "s_factor": 806.6}, {"company": "IM", "product": "iM Plus세븐UP 더좋은종신보험", "term": "20년납", "gubun": "", "s_factor": 932.4}, {"company": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "5년납", "gubun": "", "s_factor": 250.0}, {"company": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "7년납", "gubun": "", "s_factor": 400.0}, {"company": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "10년납이상", "gubun": "", "s_factor": 500.0}, {"company": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "5년납", "gubun": "", "s_factor": 220.0}, {"company": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "7년납", "gubun": "", "s_factor": 380.0}, {"company": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "10년납이상", "gubun": "", "s_factor": 450.0}, {"company": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "5년납", "gubun": "", "s_factor": 170.0}, {"company": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "7년납", "gubun": "", "s_factor": 400.0}, {"company": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "10,11년납", "gubun": "", "s_factor": 600.0}, {"company": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "12년납이상", "gubun": "", "s_factor": 600.0}, {"company": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "5년납", "gubun": "", "s_factor": 150.0}, {"company": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "7년납", "gubun": "", "s_factor": 250.0}, {"company": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "10년납이상", "gubun": "", "s_factor": 350.0}]')
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


def parse_premium(text: str) -> Optional[int]:
    """텍스트에서 보험료(원 단위)를 추출"""
    m = re.search(r'(\d+[\d,]*)\s*만\s*원?', text)
    if m:
        num = int(m.group(1).replace(',', ''))
        return num * 10000
    m2 = re.search(r'(\d+[\d,]{3,})\s*원?', text)
    if m2:
        return int(m2.group(1).replace(',', ''))
    m3 = re.search(r'(\d{1,4})', text)
    if m3:
        val = int(m3.group(1))
        if val in [5, 10, 15, 20, 25, 30, 40, 50, 100, 200, 300, 500]:
            return val * 10000
    return None


def search_life_product(company: str, query: str, term: str = "") -> Optional[Dict[str, Any]]:
    """생보사 조견표에서 가장 근접한 상품 검색 (별칭 및 하이픈 정규화 지원)"""
    comp_cleaned = company.replace('생명', '').strip()
    candidates = [p for p in LIFE_PRODUCTS if p['company'] == comp_cleaned or comp_cleaned in p['company']]
    
    if not candidates:
        return None
    
    q_norm = query.replace(" ", "").replace("-", "")
    
    # 대표 별칭 매핑
    if comp_cleaned == "DB":
        if "알행플" in q_norm:
            matched = [p for p in candidates if "알행플" in p['product']]
            if term:
                t_matched = [p for p in matched if term in p.get('term', '')]
                if t_matched: return t_matched[0]
            m10 = [p for p in matched if "10년" in p.get('term', '')]
            if m10: return m10[0]
            if matched: return matched[0]
        elif "알행" in q_norm or "리턴" in q_norm:
            matched = [p for p in candidates if "알차고" in p['product'] or "리턴" in p['product']]
            if matched: return matched[0]
        elif "올케어" in q_norm or "암종신" in q_norm:
            matched = [p for p in candidates if "올케어" in p['product']]
            if matched: return matched[0]
            
    elif comp_cleaned == "한화":
        if "건강더한" in q_norm:
            matched = [p for p in candidates if "건강더한" in p['product']]
            if term:
                t_matched = [p for p in matched if term in p.get('term', '')]
                if t_matched: return t_matched[0]
            if matched: return matched[0]
        elif "하나로" in q_norm:
            matched = [p for p in candidates if "하나로" in p['product']]
            if term:
                t_matched = [p for p in matched if term in p.get('term', '')]
                if t_matched: return t_matched[0]
            if matched: return matched[0]
        elif "제로백" in q_norm:
            matched = [p for p in candidates if "H종신" in p['product'] or "제로백" in p['product']]
            if term:
                t_matched = [p for p in matched if term in p.get('term', '')]
                if t_matched: return t_matched[0]
            if matched: return matched[0]

    elif comp_cleaned == "동양":
        if "쑥쑥" in q_norm or "어린이" in q_norm:
            matched = [p for p in candidates if "쑥쑥" in p['product']]
            if term:
                t_matched = [p for p in matched if term in p.get('term', '')]
                if t_matched: return t_matched[0]
            if matched: return matched[0]

    elif comp_cleaned == "흥국":
        if "오튼튼" in q_norm or "다사랑" in q_norm or "5튼튼" in q_norm:
            matched = [p for p in candidates if "다사랑" in p['product'] or "오튼튼" in p['product'] or "통합" in p['product']]
            if matched: return matched[0]

    keywords = [k for k in re.split(r'\s+', query) if k and k not in [comp_cleaned, '생명', '생보']]
    scored_candidates = []
    for p in candidates:
        score = 0
        p_name = p['product']
        p_term = p.get('term', '')
        p_gubun = p.get('gubun', '')
        full_text = f"{p_name} {p_term} {p_gubun}"
        
        for kw in keywords:
            kw_clean = kw.replace('-', '')
            if kw in p_name or kw_clean in p_name.replace('-', ''):
                score += 5
            elif kw in full_text or kw_clean in full_text.replace('-', ''):
                score += 2
        
        if term:
            if term in p_term:
                score += 10
            elif term.replace('년납', '').replace('년', '') in p_term:
                score += 8
                
        if score > 0:
            scored_candidates.append((score, p))
            
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    if scored_candidates:
        return scored_candidates[0][1]
    
    return None


def get_life_incentive(company: str, product_name: str, term: str, premium: int, incentive_type: str = "전략") -> Dict[str, Any]:
    comp = company.replace('생명', '').strip().lower()
    prod = product_name.replace(' ', '').lower()
    t = term.replace(' ', '')
    
    # 1. 한화생명
    if '한화' in comp:
        if '건강더한' in prod:
            if '간편' in prod:
                if '10년' in t:
                    return {"next_month": 4.0, "split": 0.5, "total": 4.5, "basis": "익월 400% + 13회차 50% (10년납 간편 450%)", "cont_bonus": 0.0, "cont_desc": "연속가동 시상 별도"}
                else:
                    return {"next_month": 3.5, "split": 1.0, "total": 4.5, "basis": "익월 350% + 13회차 100% (7년납 간편 450%)", "cont_bonus": 0.0, "cont_desc": "연속가동 시상 별도"}
            else:
                if '10년' in t:
                    return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (10년납 일반 500%)", "cont_bonus": 0.0, "cont_desc": "연속가동 시상 별도"}
                else:
                    return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (7년납 일반 500%)", "cont_bonus": 0.0, "cont_desc": "연속가동 시상 별도"}
        elif '하나로' in prod:
            if '15년' in t or '20년' in t:
                return {"next_month": 2.5, "split": 4.5, "total": 7.0, "basis": "익월 250% + 13회차 450% (15/20년납 700%, 법인 SKY지원 별도)", "cont_bonus": 0.0, "cont_desc": "월초 구간별 SKY 현금지원 연계"}
            else:
                return {"next_month": 2.5, "split": 2.5, "total": 5.0, "basis": "익월 250% + 13회차 250% (10년납 500%)", "cont_bonus": 0.0, "cont_desc": "월초 구간별 SKY 현금지원 연계"}
        elif '필요할때' in prod:
            if '12년' in t:
                return {"next_month": 3.0, "split": 5.5, "total": 8.5, "basis": "익월 300% + 13회차 550% (12년납 850%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.0, "split": 3.5, "total": 6.5, "basis": "익월 300% + 13회차 350% (10년납 650%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '밸류플러스' in prod:
            if '5년' in t:
                return {"next_month": 4.5, "split": 0.5, "total": 5.0, "basis": "익월 450% + 13회차 50% (5년납 일반 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.0, "split": 0.5, "total": 4.5, "basis": "익월 400% + 13회차 50% (7/10년납 450%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '치매담은' in prod or '간병플러스' in prod:
            if '10년' in t:
                return {"next_month": 4.5, "split": 3.5, "total": 8.0, "basis": "익월 450% + 13회차 350% (10년납 800%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '15년' in t:
                return {"next_month": 3.0, "split": 2.5, "total": 5.5, "basis": "익월 300% + 13회차 250% (15년납 550%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (20년납 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '시그니처암' in prod:
            return {"next_month": 5.0, "split": 8.0, "total": 13.0, "basis": "익월 500% + 13회차 800% (시그니처암 1,300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '시그니처' in prod or '실속가득' in prod or '통합' in prod:
            return {"next_month": 4.0, "split": 7.0, "total": 11.0, "basis": "익월 400% + 13회차 700% (통합보험 기본 1,100%)", "cont_bonus": 2.0, "cont_desc": "연속가동/조기시책 달성 시 추가 합산 가능"}
        elif 'h종신' in prod or '종신' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (H종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (기본 보장성 시책)", "cont_bonus": 0.0, "cont_desc": ""}
            
    # 2. 흥국생명
    elif '흥국' in comp:
        if any(w in prod for w in ['오튼튼', '다사랑', '3.10.5', '3.8.5', '치매담은', '건강', '암']) or incentive_type == '전략':
            return {
                "next_month": 6.0,
                "split": 8.0,
                "total": 14.0,
                "basis": "익월 600%(기본400+SKY200) + 13회차 800%(1~3주가동600+전략6종200)",
                "cont_bonus": 6.0,
                "cont_desc": "10~11월 연속가동 달성 시 +120만 원(600%) 및 핑크멤버스 +100만 원 추가 가능"
            }
        else:
            return {
                "next_month": 4.0,
                "split": 6.0,
                "total": 10.0,
                "basis": "익월 400% + 13회차 600% (일반건강 1,000%)",
                "cont_bonus": 6.0,
                "cont_desc": "10~11월 연속가동 달성 시 추가시상 가능"
            }

    # 3. 동양생명
    elif '동양' in comp:
        if '쑥쑥' in prod or '어린이' in prod:
            return {"next_month": 5.0, "split": 20.0, "total": 25.0, "basis": "익월 500% + 주간/마감분할 2,000% (쑥쑥어린이 최대 2,500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '알뜰' in prod or '종신' in prod:
            return {"next_month": 5.0, "split": 1.0, "total": 6.0, "basis": "익월 500% + 13회차 100% (알뜰종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 5.0, "split": 19.0, "total": 24.0, "basis": "익월 500% + 분할 1,900% (건강보험 최대 2,400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 4. DB생명
    elif 'db' in comp:
        if any(w in prod for w in ['알행플', '플러스', 'plus', '뉴-알행플']):
            if '7년' in t:
                return {
                    "next_month": 3.0,
                    "split": 2.0,
                    "total": 5.0,
                    "basis": "익월 300% + 13회차 200% (7년납 500%)",
                    "cont_bonus": 0.0,
                    "cont_desc": "고능률 구간시상(30만↑ 50만, 50만↑ 100만) 및 본사 체증형 지원 별도"
                }
            else:
                return {
                    "next_month": 3.0,
                    "split": 3.0,
                    "total": 6.0,
                    "basis": "익월 300% + 13회차 300% (10년납 600%, 7년납 시 500%)",
                    "cont_bonus": 0.0,
                    "cont_desc": "고능률 구간시상(30만↑ 50만, 50만↑ 100만) 및 본사 체증형 지원 별도"
                }
        elif any(w in prod for w in ['알행', '리턴', '알행종']):
            if '5년' in t:
                return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (5년납 500%)", "cont_bonus": 0.0, "cont_desc": "고능률 구간시상 별도"}
            else:
                return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "익월 400% + 13회차 400% (7/10/20년납 800%, 본사 체증형 연계)", "cont_bonus": 0.0, "cont_desc": "고능률 구간시상 별도"}
        elif any(w in prod for w in ['올케어', '암종신']):
            if '20년' in t:
                return {"next_month": 2.0, "split": 4.0, "total": 6.0, "basis": "익월 200% + 13회차 400% (20년납 600%)", "cont_bonus": 0.0, "cont_desc": "고능률 구간시상 별도"}
            else:
                return {"next_month": 4.0, "split": 6.0, "total": 10.0, "basis": "익월 400% + 13회차 600% (10/15년납 1,000%)", "cont_bonus": 0.0, "cont_desc": "고능률 구간시상 별도"}
        else:
            return {
                "next_month": 4.0,
                "split": 6.0,
                "total": 10.0,
                "basis": "익월 400% + 13회차 600% (건강보험 1,000%)",
                "cont_bonus": 2.5,
                "cont_desc": "10~11월 연속가동 팬클럽 달성 시 +50만(1구간)~150만(3구간) 추가 가능"
            }

    # 5. KB라이프
    elif 'kb' in comp:
        if '연금' in prod:
            return {"next_month": 2.0, "split": 5.0, "total": 7.0, "basis": "익월 200% + 13회차 500% (100세 든든 연금 700%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 22.5, "total": 25.5, "basis": "익월 300% + 13회차 2,250% (딱좋은 건강군 최대 2,550%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 6. 신한라이프
    elif '신한' in comp:
        if '종신' in prod or '모아' in prod:
            return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 분할 100% (모아더드림 종신 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 22.0, "total": 24.5, "basis": "익월 250% + 13회차 2,200% (통합건강 원 최대 2,450%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 7. 푸본현대
    elif '푸본' in comp:
        if '연금' in prod:
            return {"next_month": 3.0, "split": 4.0, "total": 7.0, "basis": "익월 300% + 13회차 400% (MAX연금다운 700%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '5년' in t:
            return {"next_month": 4.1, "split": 3.9, "total": 8.0, "basis": "익월 410% + 13회차 390% (MAX종신 5년납 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 2.0, "total": 5.0, "basis": "익월 300% + 13회차 200% (MAX종신 7년납 500%, 법인 SKY지원 별도)", "cont_bonus": 0.0, "cont_desc": ""}

    # 8. KDB생명
    elif 'kdb' in comp:
        if '종신' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "익월 400% + 13회차 400% (더!행복플러스종신 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '연금' in prod:
            return {"next_month": 2.0, "split": 2.5, "total": 4.5, "basis": "익월 200% + 13회차 250% (더!행복플러스UP연금 450%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 5.0, "split": 7.0, "total": 12.0, "basis": "익월 500% + 13회차 700% (라이프핏/암 1,200%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 9. ABL생명
    elif 'abl' in comp:
        if '종신' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "익월 400% + 13회차 400% (우리WON더채움종신 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 8.0, "total": 10.5, "basis": "익월 250% + 13회차 800% (우리WON건강 1,050%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 10. 농협생명
    elif '농협' in comp:
        if '종신' in prod:
            return {"next_month": 4.5, "split": 1.5, "total": 6.0, "basis": "익월 450% + 13회차 150% (투스텝NH종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 5.0, "split": 12.0, "total": 17.0, "basis": "익월 500% + 13회차 1,200% (건강플러스통합 1,700%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 11. 교보생명
    elif '교보' in comp:
        return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (모두지킴종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 12. 하나생명
    elif '하나' in comp:
        return {"next_month": 5.0, "split": 19.0, "total": 24.0, "basis": "익월 500% + 13회차 1,900% (하나로라이트 최대 2,400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 13. 미래에셋
    elif '미래' in comp:
        return {"next_month": 2.5, "split": 19.0, "total": 21.5, "basis": "익월 250% + 13회차 1,900% (M-케어 건강/암 최대 2,150%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 14. 메트라이프
    elif '메트' in comp:
        if '달러' in prod:
            return {"next_month": 2.0, "split": 2.0, "total": 4.0, "basis": "익월 200% + 13회차 200% (달러종신Plus 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.0, "split": 2.5, "total": 4.5, "basis": "익월 200% + 13회차 250% (변액리치 450%)", "cont_bonus": 0.0, "cont_desc": ""}

    return {"next_month": 0.0, "split": 0.0, "total": 0.0, "basis": "전단지별 시책 추가 확인 필요", "cont_bonus": 0.0, "cont_desc": ""}


def calculate_life(
    company: str,
    product_name: str,
    premium: int,
    s_factor: float = 1000.0,
    term: str = "20년납",
    incentive_type: str = "전략",
    include_continuous: bool = False
) -> Dict[str, Any]:
    """생명보험 수수료 및 시책 계산"""
    comp_clean = company.replace('생명', '').strip()
    
    # 1. S환산 성적 산출: P * (S환산 / 1000)
    conversion_rate = s_factor / 10.0
    s_grade = round(premium * (s_factor / 1000.0))
    
    # 2. 수수료 계산
    next_month_rate = LIFE_RULES['next_month_rate']  # 3.32 (332%)
    
    comp_inst_dict = LIFE_RULES.get('company_installments', {}).get(comp_clean, {})
    inst_rate = 1.32  # 기본값
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
    
    # 3. 시책 계산
    inc_info = get_life_incentive(comp_clean, product_name, term, premium, incentive_type)
    next_month_inc_rate = inc_info.get("next_month", 0.0)
    split_inc_rate = inc_info.get("split", 0.0)
    basis_desc = inc_info.get("basis", "")
    cont_bonus_rate = inc_info.get("cont_bonus", 0.0)
    cont_desc = inc_info.get("cont_desc", "")
    
    if include_continuous and cont_bonus_rate > 0:
        split_inc_rate += cont_bonus_rate
        basis_desc += f" [연속가동 +{int(cont_bonus_rate*100)}% 합산]"
        
    next_month_inc = round(premium * next_month_inc_rate)
    split_inc = round(premium * split_inc_rate)
    total_inc = next_month_inc + split_inc
    total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    return {
        "category": "생명보험",
        "company": comp_clean + "생명",
        "product_name": product_name,
        "term": term,
        "premium": premium,
        "s_factor": s_factor,
        "conversion_rate": round(conversion_rate, 1),
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
        "include_continuous": include_continuous
    }


def calculate_nonlife(
    company: str,
    product_name: str,
    premium: int,
    incentive_type: str = "주력",
    include_continuous: bool = False
) -> Dict[str, Any]:
    """손해보험 수수료 및 시책 계산"""
    comp_clean = company.replace('손해보험', '').replace('손보', '').replace('화재', '').replace('해상', '').strip()
    
    # 1. S환산 성적: 보험료의 92% 고정
    conv_rate = NONLIFE_RULES['conversion_rate']  # 0.92
    s_grade = round(premium * conv_rate)
    
    # 2. 수수료 계산
    next_month_rate = NONLIFE_RULES['next_month_rate']  # 6.10 (610%)
    inst_rate = NONLIFE_RULES['installment_rate']  # 1.32 (132%)
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = round(s_grade * NONLIFE_RULES['total_commission_rate'])
    
    # 3. 시책 계산
    inc_companies = NONLIFE_RULES['incentives']
    matched_comp = None
    for k in inc_companies.keys():
        if comp_clean in k or k in comp_clean:
            matched_comp = k
            break
            
    if matched_comp:
        comp_inc_dict = inc_companies[matched_comp]
        inc_rule = comp_inc_dict.get(incentive_type) or comp_inc_dict.get('주력') or list(comp_inc_dict.values())[0]
        next_month_inc_rate = inc_rule.get('next_month_base', 0.0) + inc_rule.get('next_month_sky', 0.0)
        split_inc_rate = inc_rule.get('install_week_bonus', 0.0) + inc_rule.get('install_main_bonus', 0.0) + inc_rule.get('install_sky_2nd', 0.0) + inc_rule.get('install_sky_add', 0.0)
        basis_desc = inc_rule.get('basis', '')
        cont_bonus_rate = inc_rule.get('cont_bonus_rate', 0.0)
        cont_desc = inc_rule.get('cont_desc', '')
        
        if include_continuous and cont_bonus_rate > 0:
            split_inc_rate += cont_bonus_rate
            basis_desc += f" [연속가동 +{int(cont_bonus_rate*100)}% 합산]"
            
        next_month_inc = round(premium * next_month_inc_rate)
        split_inc = round(premium * split_inc_rate)
        total_inc = next_month_inc + split_inc
        total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    else:
        next_month_inc_rate = 1.0 + 2.6
        split_inc_rate = 0.0
        next_month_inc = round(premium * next_month_inc_rate)
        split_inc = 0
        total_inc = next_month_inc
        basis_desc = "익월 360%(기본100+SKY260) (1주차 주간가동은 전단지 참조)"
        cont_bonus_rate = 0.0
        cont_desc = ""
        total_inc_rate = 360.0
        
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    full_comp_name = comp_clean + "손보" if not comp_clean.endswith(('화재', '해상')) else comp_clean
    if 'db' in comp_clean.lower() or '디비' in comp_clean:
        full_comp_name = "DB손해보험"
    elif '현대' in comp_clean:
        full_comp_name = "현대해상"
        
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
        "include_continuous": include_continuous
    }




FLYER_MAP = {
    "한화생명": "한화생명_11월.png",
    "한화": "한화생명_11월.png",
    "흥국생명": "흥국생명_11월.png",
    "흥국": "흥국생명_11월.png",
    "DB생명": "DB생명_11월.jpg",
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
    "라이나생명": "라이나생명_11월.png",
    "라이나": "라이나생명_11월.png",
    "미래에셋": "미래에셋_11월.png",
    "미래": "미래에셋_11월.png",
    "ABL생명": "ABL생명_11월.png",
    "ABL": "ABL생명_11월.png",
    "KB라이프": "KB라이프_11월.png",
    "롯데손보": "롯데손보_1주.jpg",
    "롯데": "롯데손보_1주.jpg",
    "하나손보": "하나손보_1주.jpg",
    "하나손해보험": "하나손보_1주.jpg",
    "농협손보": "농협손보_1주.jpg",
    "농협손해보험": "농협손보_1주.jpg",
    "흥국화재": "흥국화재_1주.jpg"
}

def find_flyer(comp_name: str):
    for k, v in FLYER_MAP.items():
        if k in comp_name or comp_name in k:
            return k, v
    return comp_name, "SKY_11월.jpg"

def build_flyer_response(comp_name: str) -> Dict[str, Any]:
    matched_k, filename = find_flyer(comp_name)
    encoded_comp = urllib.parse.quote(matched_k)
    encoded_filename = urllib.parse.quote(filename)
    flyer_url = f"https://skyblue-kakao-bot.onrender.com/flyer/{encoded_comp}"
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


TERM_REQUIRED_PRODUCTS = {
    "건강더한": ["7년납", "10년납"],
    "하나로": ["10년납", "15년납", "20년납"],
    "필요할때": ["10년납", "12년납"],
    "밸류플러스": ["5년납", "7년납", "10년납"],
    "치매담은": ["10년납", "15년납", "20년납"],
    "간병플러스": ["10년납", "15년납", "20년납"],
    "h종신": ["5년납", "7년납"],
    "알행플": ["7년납", "10년납", "20년납"],
    "알행리턴": ["5년납", "7년납", "10년납", "20년납"],
    "올케어": ["10년납", "15년납", "20년납"]
}

def check_term_required(product_name: str, user_text: str) -> Optional[List[str]]:
    p_norm = product_name.replace(" ", "").lower()
    t_norm = user_text.replace(" ", "").lower()
    
    # 이미 텍스트에 n년 또는 n년납이 있으면 질문 불필요
    if re.search(r'\d+\s*년', user_text):
        return None
        
    for k, terms in TERM_REQUIRED_PRODUCTS.items():
        if k in p_norm or k in t_norm:
            return terms
    return None

def build_ask_term_response(comp: str, prod_name: str, premium: int, terms: List[str]) -> Dict[str, Any]:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    
    quick_replies = [
        {
            "messageText": f"{comp} {prod_name} {prem_str} {t}",
            "action": "message",
            "label": t
        }
        for t in terms
    ]
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법 안내"})
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"📋 {comp} · {prod_name} ({prem_str})\n\n납입기간에 따라 시상률이 다릅니다. 몇 년납으로 계산해 드릴까요?\n아래 버튼을 누르시거나 직접 입력해 주세요!"
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


def parse_and_calculate(user_utterance: str, allow_term_inquiry: bool = False) -> Dict[str, Any]:
    """사용자의 자연어 메시지나 파라미터를 분석해 적절한 계산 수행"""
    text = user_utterance.strip()
    
    # 연속/연계/브릿지 시상 포함 여부 파악
    include_continuous = any(kw in text for kw in ['연속', '연계', '브릿지', '풀시상', '전체', '포함'])
    
    # 1. 보험료 추출
    premium = parse_premium(text)
    if not premium:
        premium = 200000  # 기본값 20만원
        
    # 2. 납기 추출
    m_term = re.search(r'(\d+)\s*년\s*납?', text)
    term = f"{m_term.group(1)}년납" if m_term else ""
    
    # 3. 손보사 대조 (DB손보, 현대, 메리츠, KB손보 등)
    nonlife_keywords = ['현대해상', '현대', '메리츠', 'KB손보', 'KB손', '한화손보', '한화손', 'DB손보', 'DB손', '디비손보', '디비손', '롯데손보', '롯데', '흥국화재', '농협손보', '농협손', '하나손보', '하나손', '손보', '손해보험']
    is_nonlife = any(c in text for c in nonlife_keywords)
    
    if is_nonlife:
        comp_name = "현대해상"
        if any(w in text for w in ['db', 'DB', '디비']):
            comp_name = "DB손보"
        elif any(w in text for w in ['메리츠', '화재']):
            comp_name = "메리츠"
        elif any(w in text for w in ['kb', 'KB']):
            comp_name = "KB손보"
        elif any(w in text for w in ['한화']):
            comp_name = "한화손보"
        elif any(w in text for w in ['롯데']):
            comp_name = "롯데손보"
        elif any(w in text for w in ['흥국']):
            comp_name = "흥국화재"
            
        prod_name = "주력보종"
        for p in ['퍼펙트', '간편', '굿앤굿', '주력', '종합', '자녀', '나에게맞춘', '참좋은', '훼밀리', '아이러브', '행복플러스']:
            if p in text:
                prod_name = p
                break
        return calculate_nonlife(comp_name, prod_name, premium, incentive_type="주력", include_continuous=include_continuous)
    
    # 4. 생명보험 판정
    life_companies = ['흥국', '한화', 'DB', '디비', '신한', 'KB', '메트', '농협', '동양', '라이나', '교보', 'KDB', 'ABL', '미래', '하나', '푸본', 'IM', 'IBK']
    comp_name = "흥국"
    for c in life_companies:
        if c in text:
            comp_name = "DB" if c in ['DB', '디비'] else c
            break
            
    # 상품 검색
    matched = search_life_product(comp_name, text, term=term)
    if matched:
        if allow_term_inquiry:
            needed_terms = check_term_required(matched['product'], text)
            if needed_terms:
                return {
                    "need_term_inquiry": True,
                    "company": matched['company'] + "생명",
                    "product_name": matched['product'],
                    "premium": premium,
                    "terms": needed_terms
                }
        return calculate_life(
            company=matched['company'],
            product_name=matched['product'],
            premium=premium,
            s_factor=matched['s_factor'],
            term=matched.get('term', term or "10년납" if "종신" in matched['product'] else "20년납"),
            incentive_type="전략" if "전략" in text or "오튼튼" in text or "다사랑" in text else "일반",
            include_continuous=include_continuous
        )
    else:
        if comp_name == "흥국":
            s_factor = 1100.0
            prod_name = "다사랑·오튼튼(종합)"
        elif comp_name == "한화":
            s_factor = 1140.0
            prod_name = "제로백H종신"
        elif comp_name == "동양":
            s_factor = 735.0
            prod_name = "우리WON하는쑥쑥어린이"
        elif comp_name == "DB":
            s_factor = 1020.0
            prod_name = "백년친구 뉴-알행플종신"
        else:
            s_factor = 1000.0
            prod_name = f"{comp_name}생명 일반보장"
            
        return calculate_life(
            company=comp_name,
            product_name=prod_name,
            premium=premium,
            s_factor=s_factor,
            term=term or "10년납" if "종신" in prod_name else "20년납",
            incentive_type="전략",
            include_continuous=include_continuous
        )


def format_money(val: int) -> str:
    return f"{val:,}원"


def build_kakao_response(calc_result: Dict[str, Any]) -> Dict[str, Any]:
    """카카오 i 오픈빌더 규격(ItemCard + 산출근거 설명)으로 응답 JSON 생성"""
    cat = calc_result['category']
    comp = calc_result['company']
    prod = calc_result['product_name']
    term = calc_result.get('term', '')
    premium = calc_result['premium']
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    
    sub_title = f"{comp} · {prod}"
    sub_desc = f"{term} | 월납 {format_money(premium)}" if term else f"월납 {format_money(premium)}"
    
    inc_label = "시상 소계"
    if calc_result.get('include_continuous'):
        inc_label = "시상 소계 (연속포함)"
        
    item_list = [
        {"title": "S환산 성적", "description": f"{format_money(calc_result['s_grade'])} ({calc_result['conversion_rate']}%)"},
        {"title": f"익월 수수료 ({calc_result['next_month_comm_rate']}%)", "description": format_money(calc_result['next_month_comm'])},
        {"title": f"분급 수수료 ({calc_result['installment_comm_rate']}%)", "description": format_money(calc_result['installment_comm'])},
        {"title": "수수료 소계", "description": format_money(calc_result['total_comm'])},
        {"title": f"익월 시상 ({calc_result['next_month_inc_rate']}%)", "description": format_money(calc_result['next_month_inc'])},
        {"title": f"13회차/분할시상 ({calc_result['split_inc_rate']}%)", "description": format_money(calc_result['split_inc'])},
        {"title": f"{inc_label} ({calc_result['total_inc_rate']}%)", "description": format_money(calc_result['total_inc'])},
        {"title": "👉 익월 총수령", "description": format_money(calc_result['total_next_month'])},
        {"title": "👉 분급·차년도 총수령", "description": format_money(calc_result['total_split'])}
    ]
    
    # 산출근거 텍스트 구성
    basis_desc = calc_result.get('basis_desc', '')
    basis_text = '💡 시상 산출근거: ' + str(basis_desc)
    cont_desc = calc_result.get('cont_desc', '')
    cont_bonus_rate = calc_result.get('cont_bonus_rate', 0.0)
    include_cont = calc_result.get('include_continuous', False)
    
    if include_cont:
        basis_text += ' (전월/당월 연속·연계 가동 시상 합산됨)'
    elif cont_desc:
        basis_text += ' ※ 연속·연계: ' + str(cont_desc)
        


    # 퀵리플라이 구성 (입력란 바로 위 상시 사용법 및 시책지 보기 배치)
    quick_replies = [
        {"messageText": "사용법", "action": "message", "label": "💡 사용법: 회사 상품 금액"},
        {"messageText": comp + " 시책지", "action": "message", "label": "📑 " + comp + " 시책지"}
    ]
    if not include_cont and cont_bonus_rate > 0:
        bonus_man = int(premium * cont_bonus_rate) // 10000
        btn_label = f"🔥 연속포함 (+{bonus_man}만)" if bonus_man > 0 else "🔥 연속가동 포함"
        quick_replies.append({
            "messageText": f"{comp} {prod} {prem_str} 연속포함",
            "action": "message",
            "label": btn_label
        })
    elif include_cont:
        quick_replies.append({
            "messageText": f"{comp} {prod} {prem_str}",
            "action": "message",
            "label": "📋 단건 기준만 보기"
        })
        
    if "DB손보" not in comp:
        quick_replies.append({"messageText": f"DB손보 주력 {prem_str}", "action": "message", "label": "📊 DB손보 비교"})
    if "현대해상" not in comp:
        quick_replies.append({"messageText": f"현대해상 주력 {prem_str}", "action": "message", "label": "📊 현대해상 비교"})
    if "흥국" not in comp:
        quick_replies.append({"messageText": f"흥국 오튼튼 {prem_str} 20년납", "action": "message", "label": "📊 흥국 오튼튼 비교"})
    if "한화" not in comp:
        quick_replies.append({"messageText": f"한화 건강더한 {prem_str}", "action": "message", "label": "📊 한화 건강더한 비교"})
        
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법 안내"})
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": "스카이블루에셋",
                            "description": "2026년 11월 수수료·시책 정산 결과"
                        },
                        "title": sub_title,
                        "description": sub_desc,
                        "itemList": item_list,
                        "itemListAlignment": "right",
                        "itemListSummary": {
                            "title": "🎉 최종 총수령액 합계",
                            "description": format_money(calc_result['grand_total'])
                        },
                        "buttons": [
                            {
                                "label": "📑 " + comp + " 시책지 보기",
                                "action": "webLink",
                                "webLinkUrl": "https://skyblue-kakao-bot.onrender.com/flyer/" + urllib.parse.quote(comp)
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
        "상품명과 보험료를 자유롭게 입력하시면 익월/분급 수수료와 11월 공식 시상금을 즉시 계산해 드립니다.\n\n"
        "📌 [입력 예시]\n"
        "• DB손보 10만원\n"
        "• DB손보 10만원 연속포함\n"
        "• 한화생명 건강더한종신 50만원\n"
        "• DB생명 알행플종신 10만원\n"
        "• 흥국 오튼튼 20만 20년납\n"
        "• 현대해상 주력 20만\n\n"
        "💡 전월 연속가동이나 연계 시책을 합산하고 싶으실 땐 뒤에 '연속포함'을 붙여주세요!"
    )
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": help_text}}],
            "quickReplies": [
                {"messageText": "DB손보 10만원", "action": "message", "label": "DB손보 10만원"},
                {"messageText": "한화생명 건강더한종신 50만원", "action": "message", "label": "한화 건강더한 50만"},
                {"messageText": "DB생명 알행플종신 10만원", "action": "message", "label": "DB 알행플 10만"},
                {"messageText": "흥국 오튼튼 20만 20년납", "action": "message", "label": "흥국 오튼튼 20만"},
                {"messageText": "현대해상 주력 20만", "action": "message", "label": "현대 주력 20만"}
            ]
        }
    }


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "스카이블루에셋 카카오 챗봇 스킬 서버",
        "version": "2.0.0",
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
def view_flyer_html(company_name: str):
    matched_k, filename = find_flyer(company_name)
    encoded_filename = urllib.parse.quote(filename)
    raw_cdn_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_filename}"
    local_img_url = f"/flyer-img/{filename}"
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>{matched_k} 11월 공식 시책지</title>
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
        <img src="{raw_cdn_url}" onerror="this.src='{local_img_url}'" alt="{matched_k} 시책지">
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/skill/calculate")
async def kakao_skill_calculate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return build_help_response()

    user_request = body.get("userRequest", {})
    utterance = user_request.get("utterance", "").strip()

    if not utterance or utterance in ["도움말", "사용법", "메뉴", "시작", "help", "?"]:
        return build_help_response()

    try:
        # 시책지 직접 요청 처리 (예: 한화 시책지, DB손보 시책)
        if any(kw in utterance for kw in ['시책지', '시책표', '전단지', '시책확인']):
            for k in FLYER_MAP.keys():
                if k in utterance:
                    return build_flyer_response(k)
            return build_flyer_response("스카이블루")

        calc_result = parse_and_calculate(utterance, allow_term_inquiry=True)
        if isinstance(calc_result, dict) and calc_result.get("need_term_inquiry"):
            return build_ask_term_response(
                calc_result["company"],
                calc_result["product_name"],
                calc_result["premium"],
                calc_result["terms"]
            )
        return build_kakao_response(calc_result)
    except Exception as e:
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"⚠️ 계산 중 오류가 발생했습니다: {str(e)}\n\n'DB손보 10만' 또는 '한화 건강더한 50만' 형식으로 다시 입력해 주세요."
                        }
                    }
                ]
            }
        }

class DirectCalcRequest(BaseModel):
    query: Optional[str] = None
    company: Optional[str] = None
    product_name: Optional[str] = None
    premium: Optional[int] = None
    term: Optional[str] = None
    category: Optional[str] = None
    incentive_type: Optional[str] = None
    s_factor: Optional[float] = None
    include_continuous: Optional[bool] = False

@app.post("/api/calculate")
def api_calculate(req: DirectCalcRequest):
    if req.query:
        return parse_and_calculate(req.query)

    if req.category == "손해보험" or (req.company and any(c in req.company for c in ["현대", "손보", "화재", "메리츠", "KB손", "한화손", "DB손"])):
        return calculate_nonlife(
            company=req.company or "현대해상",
            product_name=req.product_name or "주력보종",
            premium=req.premium or 200000,
            incentive_type=req.incentive_type or "주력",
            include_continuous=req.include_continuous or False
        )
    else:
        return calculate_life(
            company=req.company or "흥국",
            product_name=req.product_name or "다사랑·오튼튼",
            premium=req.premium or 200000,
            s_factor=req.s_factor or 1100.0,
            term=req.term or "20년납",
            incentive_type=req.incentive_type or "전략",
            include_continuous=req.include_continuous or False
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
