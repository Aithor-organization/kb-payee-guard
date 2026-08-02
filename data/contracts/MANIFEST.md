# Contract Corpus — MANIFEST

수집일: **2026-07-31** · 총 **160건** (실물 상용계약 151건 / 모델·템플릿 9건)

> 🔴 **실물과 모델은 절대 섞어서 집계하지 않는다.** 모델 계약서는 기안자가 조항을 빠짐없이 넣도록 설계된 문서라 조항 존재율이 구조적으로 100%에 가깝다 (아래 §2에서 실증됨). R-7의 모수는 **실물 151건**이다.


## 1. R-7 1차 측정치

| 열 | 실물 (SEC+CUAD, n=151) | 모델 (ITC, n=9) |
|---|---|---|
| `notices_clause` | **128/151 = 84.8%** | 9/9 = 100.0% |
| `amendment_clause` | **131/151 = 86.8%** | 9/9 = 100.0% |
| `payment_terms` | **119/151 = 78.8%** | 6/9 = 66.7% |
| `party_contact` | **139/151 = 92.1%** | 4/9 = 44.4% |

출처별 실물 내역:

| 열 | SEC EDGAR (n=75) | CUAD (n=76) |
|---|---|---|
| `notices` | 64/75 = 85.3% | 64/76 = 84.2% |
| `amendment` | 63/75 = 84.0% | 68/76 = 89.5% |
| `payment` | 63/75 = 84.0% | 56/76 = 73.7% |
| `contact` | 72/75 = 96.0% | 67/76 = 88.2% |

**결합 분포 (실물 151건)**

- Notices ∧ Amendment 동시 존재: **116/151 = 76.8%**
- 4개 열 전부 존재: **92/151 = 60.9%**
- Notices ∧ Amendment 둘 다 부재: 8/151 = 5.3%
- 국제거래 신호(Incoterms/CISG/L-C/B-L 등) 포함: 98/151 = 64.9%

## 2. 판정 방법과 신뢰도 (읽지 않고 숫자만 쓰지 말 것)

판정은 `detect_clauses.py`(본 디렉토리)가 수행한다. **단순 키워드 매칭이 아니다** — 초기 키워드 버전은 정밀도 ~50%였고, 수기 검수로 아래 오류를 잡아 4회 개정했다:

| 개정 계기 (수기 검수로 발견) | 조치 |
|---|---|
| `"this **contract** may not be **varied**"` (ITC/영국식 기안) 을 놓침 | 자기참조를 agreement/contract 양쪽으로 확장 |
| `"this **Supply** Agreement"` 처럼 이름 붙은 계약을 놓침 | `this [Named] Agreement` 허용 |
| `"Amendments ... **must** be in writing"` 을 놓침 | 제약어에 서법조동사(must/shall/may) 추가 |
| 양도조항(`assign, transfer or **change** any rights`)을 개정조항으로 오판 | 이전(transfer)동사 선행 시 배제 |
| 주문취소조항(`cancel, reschedule, **change** any order`)을 오판 | 동일 |
| 편입참조(`the Quality Agreement, **as amended** from time to time`)를 오판 | `as (may be) amended` 형태 배제 |
| 통지조항의 `such **changed** address` 를 개정조항으로 오판 | 뒤에 address 오면 배제 |
| `"all notices, consents, demands ... shall be in writing"` (명사 나열로 주어-동사 이격) 을 놓침 | 인접 요구 폐기, 220자 창 |

**측정된 정밀도**: body 매칭(가장 위험한 경로) 무작위 표본 **16건 수기 판독 → 16건 정정** (개정 전 동일 표본 12건 중 6건 오탐). heading 매칭은 절 제목 직접 매칭이라 위험 낮음.

**측정된 재현율**: `amendment=N` 25건 / `notices=N` 26건 전수를 수기 재검토 → 잔여 누락 각 1-2건 확인(문장분할 artifact). 따라서 위 비율은 **약 1-2%p 과소추정**이다.

🔴 **CUAD 라벨로는 R-7을 못 잰다** — CUAD의 41개 조항 라벨에 Notices/Amendment가 **없다**(Document Name, Parties, Governing Law, Anti-Assignment, Audit Rights … 41종 전수 확인). 따라서 본 수치는 CUAD 라벨이 아니라 **전문(全文)에 대한 자체 판정** 결과다.


## 3. 라이선스·이용조건

| 출처 | 건수 | 라이선스 | 재배포 |
|---|---:|---|---|
| SEC EDGAR (EX-10.x 공시본) | 75 | 미국 정부 공시자료, 저작권 비주장 (public domain 취급) | 가능 |
| CUAD v1 (Atticus Project) | 76 | **CC BY 4.0** | 가능 (출처표시 필수) |
| ITC Model Contracts | 9 | © International Trade Centre 2010. UN Digital Library 공개 PDF | ⚠️ 저작권 존속 — **로컬 분석용으로만** 사용, 재배포 금지 |

CUAD 인용: *Hendrycks et al., "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review" (NeurIPS 2021)*. SHA-256 `88b694d99007d39777fa44cd72daf8297773d285dc3eab0091ba32078888d18e` (CUAD_v1.zip, 105,883,672 B).


## 4. 전체 목록

`kind`: real=실제 체결된 상용계약 / model=모델·템플릿. `xb`=국제거래 신호.

| file | source | kind | 계약유형 | 당사자/회사 | lang | 공시일 | notices | amend | pay | contact | xb |
|---|---|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|
| `cuad-001.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | ACCURAYINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-002.txt` | CUAD v1 | real | RESELLER AGREEMENT | ADIANUTRITION,INC | EN |  | Y | Y | N | Y | Y |
| `cuad-003.txt` | CUAD v1 | real | Distributor Agreement | AIRSPANNETWORKSINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-004.txt` | CUAD v1 | real | Reseller Agreement | ASIANDRAGONGROUPINC | EN |  | Y | Y | Y | Y | N |
| `cuad-005.txt` | CUAD v1 | real | 10.1_Supply Agreement | AgapeAtpCorp | EN |  | Y | Y | Y | N | N |
| `cuad-006.txt` | CUAD v1 | real |  Manufacturing Agreement | Antares Pharma, Inc. - Manufacturing A | EN |  | Y | Y | Y | Y | Y |
| `cuad-007.txt` | CUAD v1 | real |  Manufacturing and Supply Agreement | Apollo Endosurgery - Manufacturing and | EN |  | Y | Y | Y | Y | Y |
| `cuad-008.txt` | CUAD v1 | real | Branding Agreement_ Marketing Agreement_ Investment  | AudibleInc | EN |  | Y | Y | Y | Y | N |
| `cuad-009.txt` | CUAD v1 | real | Supply Agreement | BELLICUMPHARMACEUTICALS,INC | EN |  | Y | Y | Y | Y | Y |
| `cuad-010.txt` | CUAD v1 | real | MASTER SUPPLY AGREEMENT | BELLRINGBRANDS,INC | EN |  | N | Y | Y | Y | N |
| `cuad-011.txt` | CUAD v1 | real | SUPPLY AGREEMENT | BIOFRONTERAAG | EN |  | Y | Y | Y | Y | Y |
| `cuad-012.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | BLACKBOXSTOCKSINC | EN |  | Y | Y | N | Y | Y |
| `cuad-013.txt` | CUAD v1 | real | 10.12_Manufacturing Agreement1 | BellringBrandsInc | EN |  | Y | Y | Y | Y | N |
| `cuad-014.txt` | CUAD v1 | real | 10.12_Manufacturing Agreement3 | BellringBrandsInc | EN |  | N | Y | N | Y | N |
| `cuad-015.txt` | CUAD v1 | real | 10.1_Reseller Agreement | BravatekSolutionsInc | EN |  | N | Y | Y | Y | N |
| `cuad-018.txt` | CUAD v1 | real | RESELLER AGREEMENT | DIVERSINETCORP | EN |  | Y | Y | Y | Y | Y |
| `cuad-019.txt` | CUAD v1 | real |  Manufacturing Agreement | ELECTRAMECCANICA VEHICLES CORP. - Manu | EN |  | Y | Y | N | N | Y |
| `cuad-020.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | ENTERTAINMENTGAMINGASIAINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-021.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | ETELOS,INC | EN |  | Y | Y | N | Y | N |
| `cuad-022.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | EUROPEANMICROHOLDINGSINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-023.txt` | CUAD v1 | real | 4.44_License Agreement_ Reseller Agreement | EhaveInc | EN |  | Y | Y | Y | Y | N |
| `cuad-024.txt` | CUAD v1 | real | SUPPLY AGREEMENT | FLOTEKINDUSTRIESINCCN | EN |  | Y | N | Y | Y | Y |
| `cuad-025.txt` | CUAD v1 | real |  FUSION | FUSIONPHARMACEUTICALSINC | EN |  | Y | Y | Y | Y | N |
| `cuad-026.txt` | CUAD v1 | real | 10.43_Distributor Agreement | FuseMedicalInc | EN |  | Y | Y | Y | Y | N |
| `cuad-027.txt` | CUAD v1 | real | AFFILIATE AGREEMENT | GULFSOUTHMEDICALSUPPLYINC | EN |  | Y | N | N | Y | N |
| `cuad-028.txt` | CUAD v1 | real | 6 MAT CTRCT_Distributor Agreement | GentechHoldingsInc | EN |  | Y | Y | Y | N | Y |
| `cuad-029.txt` | CUAD v1 | real |  Sales, Marketing, Distribution, and Supply Agreemen | HEMISPHERX - Sales, Marketing, Distrib | EN |  | Y | Y | Y | Y | Y |
| `cuad-030.txt` | CUAD v1 | real | EXCLUSIVE DISTRIBUTOR AGREEMENT | HYPERIONSOFTWARECORP | EN |  | N | Y | Y | Y | N |
| `cuad-031.txt` | CUAD v1 | real | 10.1_Reseller Agreement | HealthcareIntegratedTechnologiesInc | EN |  | Y | Y | Y | Y | N |
| `cuad-032.txt` | CUAD v1 | real | SUPPLY AGREEMENT | INTERSECTENT,INC | EN |  | Y | Y | Y | Y | Y |
| `cuad-033.txt` | CUAD v1 | real | 10.5_Distributor Agreement | ImineCorp | EN |  | Y | Y | Y | Y | Y |
| `cuad-034.txt` | CUAD v1 | real | 10.9_Manufacturing Agreement | InmodeLtd | EN |  | Y | Y | Y | N | Y |
| `cuad-035.txt` | CUAD v1 | real | 10.6_Distributor Agreement | InnerscopeHearingTechnologiesInc | EN |  | Y | Y | N | Y | Y |
| `cuad-036.txt` | CUAD v1 | real | 99.1_Reseller Agreement | IpassInc | EN |  | Y | Y | Y | Y | Y |
| `cuad-037.txt` | CUAD v1 | real | 4.15_Manufacturing Agreement | KitovPharmaLtd | EN |  | Y | Y | Y | Y | Y |
| `cuad-038.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | LEGACYTECHNOLOGYHOLDINGS,INC | EN |  | Y | Y | Y | N | N |
| `cuad-039.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | LIMEENERGYCO | EN |  | Y | Y | Y | Y | Y |
| `cuad-040.txt` | CUAD v1 | real | RESELLER AGREEMENT | LOYALTYPOINTINC | EN |  | Y | Y | Y | Y | N |
| `cuad-041.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | LUCIDINC | EN |  | Y | N | Y | N | Y |
| `cuad-042.txt` | CUAD v1 | real | 10.16_Supply Agreement | LohaCompanyltd | EN |  | N | N | Y | N | Y |
| `cuad-043.txt` | CUAD v1 | real | OUTSOURCING AGREEMENT | MANUFACTURERSSERVICESLTD | EN |  | Y | Y | N | Y | Y |
| `cuad-044.txt` | CUAD v1 | real | SUPPLY AGREEMENT | MEDIWOUNDLTD | EN |  | Y | Y | Y | Y | Y |
| `cuad-045.txt` | CUAD v1 | real |  Master Development and Manufacturing Agreement | Magenta Therapeutics, Inc. - Master De | EN |  | Y | Y | N | Y | Y |
| `cuad-046.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | NANOPHASETECHNOLOGIESCORP | EN |  | Y | Y | Y | Y | Y |
| `cuad-047.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | NEOMEDIATECHNOLOGIESINC | EN |  | N | Y | N | Y | N |
| `cuad-048.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT_New | NEONSYSTEMSINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-049.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | NETGEAR,INC | EN |  | Y | Y | Y | Y | N |
| `cuad-050.txt` | CUAD v1 | real | 10.36_Manufacturing Agreement_ Supply Agreement | NeuroboPharmaceuticalsInc | EN |  | Y | N | Y | Y | Y |
| `cuad-051.txt` | CUAD v1 | real | RESELLER AGREEMENT | OMINTO,INC | EN |  | Y | Y | N | Y | N |
| `cuad-052.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | OPTIMIZEDTRANSPORTATIONMANAGEMENT,INC | EN |  | N | Y | N | Y | N |
| `cuad-053.txt` | CUAD v1 | real |  A_R STRATEGIC LICENSING, DISTRIBUTION AND MARKETING | PACIRA PHARMACEUTICALS, INC. - A | EN |  | Y | Y | Y | Y | N |
| `cuad-054.txt` | CUAD v1 | real | SUPPLY AGREEMENT | PROFOUNDMEDICALCORP | EN |  | Y | Y | Y | Y | Y |
| `cuad-055.txt` | CUAD v1 | real | Purchase Agreement1 | PlayboyEnterprisesInc | EN |  | Y | Y | Y | Y | N |
| `cuad-056.txt` | CUAD v1 | real | 10.18_Supply Agreement | ReynoldsConsumerProductsInc | EN |  | Y | Y | N | Y | Y |
| `cuad-057.txt` | CUAD v1 | real | SUPPLY AGREEMENT | SEASPINEHOLDINGSCORP | EN |  | Y | Y | Y | Y | N |
| `cuad-058.txt` | CUAD v1 | real | 10.2_Distributor Agreement | ScansourceInc | EN |  | N | Y | N | Y | Y |
| `cuad-059.txt` | CUAD v1 | real | 10.38_Distributor Agreement1 | ScansourceInc | EN |  | Y | Y | Y | Y | Y |
| `cuad-060.txt` | CUAD v1 | real | 10.38_Distributor Agreement2 | ScansourceInc | EN |  | N | N | N | N | Y |
| `cuad-061.txt` | CUAD v1 | real | 10.39_Distributor Agreement | ScansourceInc | EN |  | N | N | N | Y | N |
| `cuad-062.txt` | CUAD v1 | real |  STRATEGIC SALES _ MARKETING AGREEMENT | SightLife Surgical, Inc. - STRATEGIC S | EN |  | Y | Y | N | Y | N |
| `cuad-063.txt` | CUAD v1 | real | 6 MAT CTRCT_Distributor Agreement | SmartRxSystemsInc | EN |  | Y | Y | Y | Y | N |
| `cuad-064.txt` | CUAD v1 | real |  Manufacturing Agreement  | Sonos, Inc. - Manufacturing Agreement  | EN |  | Y | Y | Y | Y | Y |
| `cuad-065.txt` | CUAD v1 | real | 10.37_Distributor Agreement | StaarSurgicalCompany | EN |  | Y | Y | Y | N | Y |
| `cuad-066.txt` | CUAD v1 | real | 4.10_Marketing Agreement_ Reseller Agreement | TodosMedicalLtd | EN |  | N | Y | N | Y | Y |
| `cuad-067.txt` | CUAD v1 | real | SUPPLY AGREEMENT | ULTRAGENYXPHARMACEUTICALINC | EN |  | Y | Y | N | Y | Y |
| `cuad-068.txt` | CUAD v1 | real | 2.6_Manufacturing Agreement_ Supply Agreement | UpjohnInc | EN |  | Y | Y | Y | Y | Y |
| `cuad-069.txt` | CUAD v1 | real |  Manufacturing and Supply Agreement | VAPOTHERM, INC. - Manufacturing and Su | EN |  | Y | Y | Y | Y | Y |
| `cuad-070.txt` | CUAD v1 | real | SUPPLY AGREEMENT | VAXCYTE,INC | EN |  | Y | Y | N | Y | N |
| `cuad-071.txt` | CUAD v1 | real | SUPPLY AGREEMENT | VERICELCORP | EN |  | Y | Y | Y | Y | Y |
| `cuad-072.txt` | CUAD v1 | real | DISTRIBUTOR AGREEMENT | VISIUMTECHNOLOGIES,INC | EN |  | Y | Y | Y | Y | Y |
| `cuad-073.txt` | CUAD v1 | real | PROMOTION AND DISTRIBUTION AGREEMENT | WHITESMOKE,INC | EN |  | Y | N | Y | Y | N |
| `cuad-074.txt` | CUAD v1 | real | RESELLER AGREEMENT | WORLDWIDESTRATEGIESINC | EN |  | Y | Y | Y | Y | Y |
| `cuad-075.txt` | CUAD v1 | real | 10.12_Distributor Agreement | WaterNowInc | EN |  | Y | Y | Y | Y | N |
| `cuad-076.txt` | CUAD v1 | real | 10.1_Supply Agreement | WestPharmaceuticalServicesInc | EN |  | Y | Y | Y | Y | Y |
| `cuad-077.txt` | CUAD v1 | real | 10.2_Distributor Agreement | ZogenixInc | EN |  | Y | Y | Y | Y | Y |
| `cuad-078.txt` | CUAD v1 | real |  MANUFACTURING DESIGN MARKETING AGREEMENT | Zounds Hearing, Inc. - MANUFACTURING D | EN |  | N | Y | Y | Y | N |
| `itc-01-contractual-alliance.txt` | ITC (UN) | model | International Contractual Alliance | (template) | EN | 2010 | Y | Y | N | N | N |
| `itc-02-corporate-joint-venture.txt` | ITC (UN) | model | International Corporate Joint Venture | (template) | EN | 2010 | Y | Y | N | N | N |
| `itc-03-sale-of-goods-short.txt` | ITC (UN) | model | International Commercial Sale of Goods (short versio | (template) | EN | 2010 | Y | Y | Y | Y | Y |
| `itc-04-sale-of-goods-standard.txt` | ITC (UN) | model | International Commercial Sale of Goods (standard ver | (template) | EN | 2010 | Y | Y | Y | N | Y |
| `itc-05-long-term-supply-of-goods.txt` | ITC (UN) | model | International Long-Term Supply of Goods | (template) | EN | 2010 | Y | Y | Y | N | Y |
| `itc-06-contract-manufacture.txt` | ITC (UN) | model | International Contract Manufacture Agreement | (template) | EN | 2010 | Y | Y | Y | Y | Y |
| `itc-07-distribution-of-goods.txt` | ITC (UN) | model | International Distribution of Goods | (template) | EN | 2010 | Y | Y | Y | Y | Y |
| `itc-08-commercial-agency.txt` | ITC (UN) | model | International Commercial Agency | (template) | EN | 2010 | Y | Y | Y | N | N |
| `itc-09-supply-of-services.txt` | ITC (UN) | model | International Supply of Services | (template) | EN | 2010 | Y | Y | N | Y | N |
| `sec-001.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | MANNATECH INC  (MTEX) | EN | 2004-12-17 | Y | N | Y | Y | N |
| `sec-002.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | GRANT PRIDECO INC | EN | 2004-03-15 | Y | Y | Y | Y | Y |
| `sec-003.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | CARRINGTON LABORATORIES INC /TX/ | EN | 2005-03-28 | Y | N | Y | Y | N |
| `sec-005.txt` | SEC EDGAR | real | SUPPLY AGREEMENT DATED JULY 30, 2004 BTWN BIOMARIN A | BIOMARIN PHARMACEUTICAL INC  (BMRN) | EN | 2005-03-16 | Y | Y | Y | Y | Y |
| `sec-009.txt` | SEC EDGAR | real | MASTER SUPPLY AGREEMENT, DATE JUNE 13, 2003 | MEMRY CORP | EN | 2003-09-29 | Y | Y | Y | Y | Y |
| `sec-010.txt` | SEC EDGAR | real | NEWBURY PARK WAFER SUPPLY AND SERVICES AGREEMENT | SKYWORKS SOLUTIONS INC  (SWKS) | EN | 2002-12-23 | Y | Y | Y | Y | Y |
| `sec-012.txt` | SEC EDGAR | real | DURECT SUPPLY AGREEMENT | DURECT CORP  (DRRX) | EN | 2001-03-30 | Y | Y | N | Y | N |
| `sec-015.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | SERACARE LIFE SCIENCES INC | EN | 2002-12-30 | Y | Y | Y | Y | Y |
| `sec-016.txt` | SEC EDGAR | real | SUPPLY AGREEMENT DATED 1/1/01 | CORN PRODUCTS INTERNATIONAL INC  (INGR | EN | 2001-03-27 | Y | Y | N | Y | N |
| `sec-017.txt` | SEC EDGAR | real | SUPPLY AGREEMENT, DATED JANUARY 17, 2007 | HOKU SCIENTIFIC INC | EN | 2007-06-29 | Y | Y | Y | Y | Y |
| `sec-020.txt` | SEC EDGAR | real | SUPPLY AGREEMENT - PEPSI-COLA ADVERTISING AND MARKET | CONSTAR INTERNATIONAL INC | EN | 2009-03-31 | Y | Y | Y | Y | Y |
| `sec-023.txt` | SEC EDGAR | real | EX-10.12 REAGENT SUPPLY AGREEMENT | SURMODICS INC  (SRDX) | EN | 2002-12-30 | N | Y | N | Y | N |
| `sec-024.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | MANNATECH INC  (MTEX) | EN | 2004-03-15 | Y | N | Y | Y | N |
| `sec-025.txt` | SEC EDGAR | real | AMENDED & RESTATED SUPPLY AGREEMENT WITH JIANGXI JIN | HOKU SCIENTIFIC INC | EN | 2009-06-15 | Y | Y | Y | Y | Y |
| `sec-026.txt` | SEC EDGAR | real | MANUFACTURING AGREEMENT WITH PRODUITS CHEMQUES AUXIL | CORCEPT THERAPEUTICS INC  (CORT) | EN | 2007-04-02 | Y | Y | Y | Y | Y |
| `sec-027.txt` | SEC EDGAR | real | SUPPLY CONTRACT WITH MONARCH | AIRSPAN NETWORKS INC | EN | 2002-03-28 | Y | Y | Y | Y | Y |
| `sec-028.txt` | SEC EDGAR | real | MANUFACTURING SUPPLY AGREEMENT | ANDREW CORP | EN | 2006-12-13 | Y | Y | Y | Y | Y |
| `sec-029.txt` | SEC EDGAR | real | SUPPLY & MANUFACTURE AGREEMENT | AMERICAN TECHNOLOGY CORP /DE/  (GNSS) | EN | 2002-12-23 | Y | Y | Y | Y | N |
| `sec-030.txt` | SEC EDGAR | real | MASTER DEVELOPMENT AND SUPPLY AGREEMENT | MULTI FINELINE ELECTRONIX INC | EN | 2008-12-09 | N | Y | Y | N | Y |
| `sec-031.txt` | SEC EDGAR | real | EX-10.40 ACCESS CONTROL SUPPLY AGREEMENT | AMERICAN BUILDING CONTROL INC | EN | 2003-04-04 | Y | Y | Y | Y | Y |
| `sec-032.txt` | SEC EDGAR | real | THIRD AMENDED AND RESTATED MEMBRANE MANUFACTURE AND  | ENTEGRIS INC  (ENTG) | EN | 2010-02-26 | Y | Y | Y | Y | Y |
| `sec-033.txt` | SEC EDGAR | real | DEVELOPMENT AND SUPPLY AGREEMENT | BIO IMAGING TECHNOLOGIES INC | EN | 2007-03-29 | Y | Y | Y | Y | Y |
| `sec-035.txt` | SEC EDGAR | real | SUPPLY AND LICENSE AGREEMENT | ORTHOVITA INC | EN | 2008-03-17 | Y | Y | N | Y | Y |
| `sec-036.txt` | SEC EDGAR | real | POLYSILICON SUPPLY AGREEMENT, DATED DECEMBER 22, 200 | SUNPOWER CORP  (SPWRQ) | EN | 2007-03-02 | Y | Y | Y | Y | Y |
| `sec-037.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | AMYLIN PHARMACEUTICALS INC | EN | 2012-02-22 | Y | Y | Y | Y | Y |
| `sec-038.txt` | SEC EDGAR | real | INGOT SUPPLY AGREEMENT, DATED DECEMBER 22, 2006 | SUNPOWER CORP  (SPWRQ) | EN | 2007-03-02 | Y | Y | Y | Y | Y |
| `sec-039.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | COTT CORP /CN/  (PRMW) | EN | 2016-02-29 | N | N | Y | Y | N |
| `sec-040.txt` | SEC EDGAR | real | MANUFACTURING PREPARATION AND SERVICES AGREEMENT | PALATIN TECHNOLOGIES INC  (PTN) | EN | 2016-09-19 | Y | Y | N | Y | Y |
| `sec-041.txt` | SEC EDGAR | real | STRATEGIC ALLIANCE AND SUPPLY AGREEMENT | Vista International Technologies Inc | EN | 2010-04-15 | Y | Y | Y | Y | N |
| `sec-042.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | BIOMIMETIC THERAPEUTICS, INC. | EN | 2008-03-12 | Y | Y | Y | Y | Y |
| `sec-043.txt` | SEC EDGAR | real | EX-10.II.B.4: EXTERNAL MANUFACTURING SERVICES AGREEM | LUCENT TECHNOLOGIES INC | EN | 2005-12-14 | Y | Y | Y | Y | Y |
| `sec-044.txt` | SEC EDGAR | real | COMMERCIAL DEVELOPMENT AND CLINICAL SUPPLY AGREEMENT | NutriBand Inc.  (NTRB, NTRBW) | EN | 2025-04-28 | Y | Y | N | Y | N |
| `sec-045.txt` | SEC EDGAR | real | SUPPLY AGREEMENT DATED AS OF MAY 1, 2001 | ALLIANCE LAUNDRY SYSTEMS LLC | EN | 2002-03-06 | Y | N | Y | Y | Y |
| `sec-046.txt` | SEC EDGAR | real | AMENDED MANUFACTURING AND SUPPLY AGREEMENT | DENDREON CORP | EN | 2003-03-14 | Y | Y | N | Y | Y |
| `sec-047.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | ALLIANCE LAUNDRY SYSTEMS LLC | EN | 2003-03-12 | Y | N | Y | Y | Y |
| `sec-048.txt` | SEC EDGAR | real | THROMBIN JMI SUPPLY AGREEMENT | VASCULAR SOLUTIONS INC | EN | 2007-02-02 | Y | Y | Y | Y | Y |
| `sec-049.txt` | SEC EDGAR | real | DEVICE SUPPLY AGREEMENT | VASCULAR SOLUTIONS INC | EN | 2007-02-02 | Y | Y | Y | Y | Y |
| `sec-050.txt` | SEC EDGAR | real | DEVELOPMENT, LICENSE AND SUPPLY AGREEMENT | ENZON INC  (ENZN) | EN | 2002-09-26 | Y | Y | Y | Y | N |
| `sec-051.txt` | SEC EDGAR | real | AMENDED SUPPLY AGREEMENT BY AND BETWEEN THE COMPANY  | MYOS RENS TECHNOLOGY INC.  (MDVLQ) | EN | 2017-03-31 | Y | Y | Y | Y | N |
| `sec-052.txt` | SEC EDGAR | real | SUPPLY AGREEMENT DATED JULY 31, 2005 | CYGNE DESIGNS INC | EN | 2005-08-04 | Y | Y | Y | Y | Y |
| `sec-053.txt` | SEC EDGAR | real | LONG-TERM SUPPLY AGREEMENT | Islet Sciences, Inc | EN | 2012-07-27 | N | Y | Y | Y | Y |
| `sec-054.txt` | SEC EDGAR | real | MASTER TERM AND CONDITIONS SUPPLY AGREEMENT | Loop Industries, Inc.  (LOOP) | EN | 2018-11-29 | Y | N | Y | N | Y |
| `sec-056.txt` | SEC EDGAR | real | WATSON SUPPLY AGREEMENT | STELLAR PHARMACEUTICALS INC | EN | 2006-12-22 | Y | Y | Y | Y | Y |
| `sec-057.txt` | SEC EDGAR | real | MASTER SUPPLY AGREEMENT, EFFECTIVE AS OF AUGUST 1, 2 | MEMRY CORP | EN | 2006-08-10 | Y | Y | Y | Y | Y |
| `sec-058.txt` | SEC EDGAR | real | SUPPLY AGREEMENT | NeurogesX Inc | EN | 2009-07-01 | Y | Y | Y | Y | Y |
| `sec-059.txt` | SEC EDGAR | real | MASTER INNOVATION AND SUPPLY AGREEMENT | HERSHEY CO  (HSY) | EN | 2007-07-19 | Y | Y | Y | Y | Y |
| `sec-060.txt` | SEC EDGAR | real | PURCHASE AND SUPPLY AGREEMENT, DATED AS OF SEPTEMBER | VISTEON CORP  (VC) | EN | 2005-10-06 | Y | Y | Y | Y | Y |
| `sec-061.txt` | SEC EDGAR | real | SUPPLY AGREEMENT BY AND BETWEEN NVE CORPORATION AND  | NVE CORP /NEW/  (NVEC) | EN | 2009-05-06 | N | Y | Y | Y | Y |
| `sec-062.txt` | SEC EDGAR | real | EX-10.64 VIVENDI DISTRIBUTION AGREEMENT #4 | INTERPLAY ENTERTAINMENT CORP | EN | 2003-04-01 | N | N | N | Y | N |
| `sec-063.txt` | SEC EDGAR | real | EX-10.65 VIVENDI DISTRIBUTION AGREEMENT #5 | INTERPLAY ENTERTAINMENT CORP | EN | 2003-04-01 | N | N | N | Y | N |
| `sec-064.txt` | SEC EDGAR | real | 10.3H BOVINE VACCINE DISTRIBUTION AGREEMENT | HESKA CORP | EN | 2002-05-23 | Y | Y | Y | Y | N |
| `sec-065.txt` | SEC EDGAR | real | MICROSOFT OEM MOBILE WINDOWS DISTRIBUTION AGREEMENT | BSQUARE CORP /WA | EN | 2011-03-17 | Y | Y | Y | Y | Y |
| `sec-066.txt` | SEC EDGAR | real | MASTER DISTRIBUTION AGREEMENT | ASPECT MEDICAL SYSTEMS INC | EN | 2001-03-29 | Y | Y | Y | Y | Y |
| `sec-067.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT | Sonoma Pharmaceuticals, Inc.  (SNOA) | EN | 2017-06-28 | Y | Y | Y | Y | Y |
| `sec-068.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT DATED SEPTEMBER 25, 1995 | ALTEON INC /DE | EN | 2001-03-02 | Y | Y | Y | Y | Y |
| `sec-069.txt` | SEC EDGAR | real | EXCLUSIVE DISTRIBUTION AGREEMENT | OxySure Systems Inc | EN | 2015-03-31 | Y | Y | Y | Y | Y |
| `sec-070.txt` | SEC EDGAR | real | SALES AND DISTRIBUTIOIN AGREEMENT | HEMISPHERX BIOPHARMA INC  (AIM) | EN | 2003-05-20 | Y | Y | Y | Y | N |
| `sec-071.txt` | SEC EDGAR | real | NATIONAL BRAND DISTRIBUTION AGREEMENT | SRI SURGICAL EXPRESS INC | EN | 2010-03-31 | Y | Y | Y | Y | N |
| `sec-072.txt` | SEC EDGAR | real | EXCLUSIVE DISTRIBUTION AGREEMENT | MPHASE TECHNOLOGIES INC  (XDSL) | EN | 2004-01-28 | N | Y | Y | Y | N |
| `sec-073.txt` | SEC EDGAR | real | LICENSE AND DISTRIBUTION AGREEMENT | SUPERIOR UNIFORM GROUP INC  (SGC) | EN | 2011-02-25 | Y | Y | Y | Y | Y |
| `sec-074.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT BY AND BETWEEN MACROMEDIA, IN | MACROMEDIA INC | EN | 2004-06-14 | Y | Y | Y | Y | Y |
| `sec-076.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT | ATARI INC | EN | 2004-06-14 | Y | Y | Y | Y | Y |
| `sec-077.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT | POPULAR INC  (BPOP, BPOPM, BPOPO) | EN | 2001-03-16 | Y | N | Y | Y | N |
| `sec-078.txt` | SEC EDGAR | real | LICENSE, DEVELOPMENT, SUPPLY & DISTRIBUTION AGREEMEN | IMMUNICON CORP | EN | 2007-03-15 | Y | Y | Y | Y | Y |
| `sec-079.txt` | SEC EDGAR | real | EXCLUSIVE DISTRIBUTION AGREEMENT | VIVUS INC | EN | 2003-03-17 | Y | Y | Y | Y | Y |
| `sec-081.txt` | SEC EDGAR | real | EXCLUSIVE DISTRIBUTION AGREEMENT | BIOSPHERE MEDICAL INC | EN | 2002-04-01 | Y | Y | N | Y | Y |
| `sec-082.txt` | SEC EDGAR | real | MARKETIING AND DISTRIBUTION AGREEMENT | APPLERA CORP | EN | 2004-09-09 | N | Y | N | N | N |
| `sec-083.txt` | SEC EDGAR | real | REVISED DISTRIBUTION AGREEMENT DATED JUNE 25, 2012 B | ETERNITY HEALTHCARE INC. | EN | 2012-07-19 | Y | Y | Y | Y | Y |
| `sec-084.txt` | SEC EDGAR | real | EX. 10.61 - MASTER DISTRIBUTION AGREEMENT | INNOVO GROUP INC | EN | 2004-02-27 | Y | Y | Y | Y | Y |
| `sec-086.txt` | SEC EDGAR | real | AMENDED & RESTATED DISTRIBUTION AGREEMENT | MACKENZIE INVESTMENT MANAGEMENT INC | EN | 2002-07-09 | N | N | N | Y | N |
| `sec-087.txt` | SEC EDGAR | real | DISTRIBUTION AGREEMENT BY AND BETWEEN JAMBA JUICE CO | JAMBA, INC. | EN | 2007-04-02 | Y | Y | Y | Y | Y |
| `sec-088.txt` | SEC EDGAR | real | INTERNATIONAL DISTRIBUTOR AGREEMENT | CASTELLE \CA\ | EN | 2007-03-30 | N | N | Y | Y | N |
| `sec-089.txt` | SEC EDGAR | real | DISTRIBUTOR AGREEMENT DATED OCTOBER 31, 2006 BETWEEN | PENSKE AUTOMOTIVE GROUP, INC.  (PAG) | EN | 2008-02-26 | Y | Y | Y | Y | Y |
| `sec-090.txt` | SEC EDGAR | real | EX-10.4 AUTHORIZED DISTRIBUTOR AGREEMENT FOR 2003 | XETA TECHNOLOGIES INC | EN | 2004-01-16 | Y | Y | Y | Y | Y |
| `sec-091.txt` | SEC EDGAR | real | DISTRIBUTOR AGREEMENT | SIELOX INC | EN | 2008-03-31 | Y | Y | Y | Y | N |

## 5. 접근 불가 / 미수집 소스

| 소스 | 상태 | 사유 |
|---|---|---|
| ICC Model International Sale Contract | ❌ 미수집 | ICC Knowledge2Go 유료 판매물(약 €40). 공개 전문 없음 — 우회하지 않음 |
| KITA 표준 무역계약서 | ❌ 미수집 | `kita.net/board/format` 서식 다운로드가 세션/로그인 기반(`JSESSIONID_KITA`). 비로그인 직접 접근 불가 |
| UNCITRAL 모델 계약서 | ➖ 해당없음 | UNCITRAL은 CISG(협약 본문)·모델**법**을 발행하며 체결용 계약서식은 발행하지 않음. 실질 대체재가 ITC 모델계약서(§4 itc-*)임 |
| KOTRA / 중기부 템플릿 | ⏸ 미시도 | ITC 9종으로 모델계약 표본이 충분해 우선순위 낮춤. 필요 시 추가 가능 |
| SEC EDGAR 전문검색 2001년 이전 | ⚠️ 부분 | EDGAR full-text search 색인이 2001+만 커버. 그 이전 계약은 미포함 |

## 6. 파일 구성

```
data/contracts/
  sec-*.txt            SEC EDGAR Exhibit 10.x 본문 (HTML→텍스트 추출)
  cuad-*.txt           CUAD v1 full_contract_txt 중 교역계약 부분집합
  itc-*.txt            ITC 모델계약 9종 (PDF→텍스트, 장별 분할)
  _raw/                SEC 원본 HTML
  detect_clauses.py    조항 판정기 (본 MANIFEST 수치 생성기)
  _detect.json         파일별 4개 열 판정 결과
  _evidence.json       판정 근거 문장 (전건 수기 검증 가능)
  _sec_meta.json / _cuad_meta.json   출처 메타데이터
```

재현: `python3 detect_clauses.py` (표준 라이브러리만 사용, 의존성 없음)

---

## 7. 무역·국문 확장 수집 (2026-08-02)

> 기존 §1~§5(미국 상용계약 151 + ITC 모델 9)는 **그대로 둔다**. 본 절은 그 위에 얹는 **무역 전용 영문 62건 + 국문 49건**이다. 세 모집단은 **절대 합산하지 않는다** — §7-3에서 보듯 조항 존재율이 서로 크게 다르다.

### 7-1. 확보 현황

| 구분 | 건수 | 목표 | 성격 | 출처 | 라이선스 | 재배포 |
|---|---:|---:|---|---|---|:--:|
| 무역/수출입 영문 `trade-NNN.txt` | **62** | 30+ | 실물 상용계약 | SEC EDGAR 전문검색 (EX-10.x/EX-4.x/EX-2.x) | 미국 정부 공시자료 (public domain 취급) | 가능 |
| 국문 `kr-NNN.txt` | **49** | 20+ | **표준서식** (실물 아님) | 국가법령정보센터 law.go.kr (계약예규·고시·훈령·예규·지침·공고) | **저작권법 제7조제2호** — 국가의 고시·공고·훈령 그 밖에 이와 유사한 것은 저작권 보호 대상 아님 | 가능 |

🔴 **국문 49건은 전부 표준서식이다. 실물 국문 계약서는 0건.** MANIFEST §1의 "실물과 모델을 섞지 않는다" 규율이 그대로 적용된다 — 표준서식은 기안자가 조항을 빠짐없이 넣도록 설계된 문서이므로 존재율이 실물보다 높게 나오는 방향으로 편향된다. 다만 §7-3에서 보듯 **국문 표준서식의 notices는 오히려 26.5%로 극단적으로 낮다** — 편향 방향이 조항마다 다르므로 일괄 보정은 불가능하다.

### 7-2. 판정 방법

- **영문 62건**: 본 디렉토리 `detect_clauses.py` (v4) **그대로** 사용. 기존 151건과 동일 코드 → 비교 가능.
- **국문 49건**: 영문 v4의 *의미론*을 한국어로 옮긴 별도 검출기로 판정. 코드는 **`detect_clauses_kr.py`** (본 디렉토리, `detect_clauses.py` 옆. 프로젝트 `src/`·`tests/`·`scripts/` 미변경). 영문 v4가 그랬듯 **수기 감사로 4회 개정**했다:

| 수기 감사로 발견한 오류 | 조치 |
|---|---|
| 한국어 조 제목은 **서술형**이다 — `제24조(납품예정일자의 통지)`, `제12조(변동사항 통보의무)`, `제26조(선적 통보)`. 제목에 "통지"가 들어간다고 §Notices로 세면 **34건 중 21건이 오탐** | 제목이 *통지 그 자체에 관한 것*일 때만 인정 (`통지`/`통지 등`/`통지방법`/`상호통지`/`회원에 대한 통지 및 공지`). 사건 특정 수식어가 붙으면 배제 |
| 본문 경로에서 `지체 없이 계약담당공무원에게 서면으로 통지하여야 한다`(개별 의무)를 §Notices로 오판 — 7건 전부 오탐 | 통지어 **직전**에 총칭(`모든`/`일체의`/`각종`) 또는 이 계약 범위 지정이 있어야 하고, **직후 220자**에 실제 전달수단·도달간주 규칙이 있어야 함 |
| `하수급인의 변경 또는 하도급 계약내용의 변경을 요구할 수 있다`(kr-024)를 §Amendment로 오판 | 변경 대상이 **타인·타 계약**(하도급/하수급인/구성원/대표자/주소)이면 배제. `계약금액`·`계약기간`은 자기참조에서 제외 — 한국 공공계약의 `계약금액의 조정`은 별개 제도 |
| `약관의 변경 등`·`약관의 개정`(kr-013/014/036)을 놓침 | 약관형 문서의 변경조항을 제목 패턴에 추가 |
| `대가의 지급, 기성검사 … 등은 일반조건에서 정한 바에 따른다`(편입참조)를 결제조건으로 오판 | 편입참조 어미 배제 + 결제어 **직후 80자** 내 지급의무 표현 요구. `지불`·`정보제공료`·`대금결제` 어휘 누락도 함께 보정 |

**정밀도 감사 결과**: 국문 판정 전건에 대해 근거 문장/제목을 출력해 수기 판독. notices Y 13건 전수 확인(오탐 0), amendment 본문매칭 4건 전수 확인(오탐 0), payment 본문매칭 전수 확인. 재현율 감사는 N 판정 전건의 조 제목 목록을 훑어 누락 조항을 역추적(→ 약관 변경조항 3건, kr-029 `제21조(대금결제)` 1건 복구).

⚠️ **약한 판정 1종을 명시한다**: amendment Y 41건 중 **5건**(kr-001/002/003/004/037)은 `기타 계약내용의 변경으로 인한 계약금액의 조정` 제목으로만 잡힌다. 이는 계약변경을 *전제로* 금액을 조정하는 조항이지 "서면 합의로만 변경" 조항이 아니다. 이 5건을 빼면 **36/49 = 73.5%**. 아래 표는 넓은 정의(83.7%)를 싣되 두 값을 함께 보고한다.

### 7-3. 🎯 핵심 산출물 — 모집단별 조항 존재율

| 모집단 | n | notices | amendment | payment_terms | contact | **email** |
|---|---:|---:|---:|---:|---:|---:|
| **무역 영문** (실물) | 62 | 32/62 = **51.6%** | 43/62 = **69.4%** | 51/62 = **82.3%** | 53/62 = 85.5% | 7/62 = **11.3%** |
| **국문** (표준서식) | 49 | 13/49 = **26.5%** | 41/49 = **83.7%** (엄격 73.5%) | 38/49 = **77.6%** | 30/49 = 61.2% | 0/49 = **0.0%** |
| (참고) 기존 미국 상용 실물 | 151 | 128/151 = 84.8% | 131/151 = 86.8% | 119/151 = 78.8% | 139/151 = 92.1% | 30/151 = 19.9% |
| (참고) ITC 모델 (재배포 금지) | 9 | 100.0% | 100.0% | 66.7% | 44.4% | 11.1% |

**읽는 법 — 세 가지가 뒤집혔다**

1. 🔴 **§Notices가 무너진다.** 미국 상용 84.8% → 무역 영문 51.6% → 국문 26.5%. 무역 계약서는 짧은 매매계약(sales contract)이 많아 통지 *메커니즘* 조항 자체를 두지 않고, 국문 공공 표준서식은 통지 절차를 **국가계약법령에 위임**하기 때문에 문서 안에 없다. → 통지조항을 전제하는 탐지 로직은 실제 대상 문서의 **과반에서 발화하지 않는다**.
2. ✅ **결제조건은 오히려 올라간다.** 78.8% → 82.3%. 무역계약은 L/C·T/T·Incoterms를 본문에 반드시 적기 때문이다. S10(결제조건 대조)은 실제 대상에서 **더 자주 발화한다**.
3. 🔴 **이메일이 사실상 사라진다.** 19.9% → 무역 11.3% → 국문 **0.0%**. 국문 표준서식은 당사자 기재란이 별지 서식으로 분리돼 본문에 연락처가 아예 없다. → 이메일 주소를 앵커로 삼는 탐지는 국문에서 **전면 무효**다.

**amendment**: 미국 86.8% → 무역 69.4% → 국문 83.7%(엄격 73.5%). 무역계약의 하락폭이 가장 크다.

**무역 영문에서 amendment/change order 10건을 뺀 완결계약 52건만**(§7-4 `doc_type=agreement`):

| n | notices | amendment | payment_terms | contact | email |
|---:|---:|---:|---:|---:|---:|
| 52 | 31/52 = **59.6%** | 39/52 = **75.0%** | 46/52 = **88.5%** | 46/52 = 88.5% | 7/52 = 13.5% |

부분문서를 제외해도 결론은 같다 — notices는 미국 상용 84.8% 대비 **25%p 낮고**, payment_terms는 78.8% 대비 **10%p 높다**. 방향이 뒤집힌 것은 표본 구성 artifact가 아니다.

### 7-4. 무역 영문 목록 (`trade-NNN.txt`, n=62)

전부 SEC EDGAR 공시본 · 실물 · EN · 무역여부 Y · public domain · 재배포 가능.

| 파일 | 회사 | exhibit | 공시일 | 종류 | 무역신호 | notices | amend | pay | email |
|---|---|---|---|---|---|:--:|:--:|:--:|:--:|
| `trade-001.txt` | ACCELR8 TECHNOLOGY CORP  (AXDX) | EX-10.1 | 2005-06-08 | agreement | incoterms,fobcif,customs,ship | Y | Y | Y | N |
| `trade-002.txt` | ACORN HOLDING CORP | EX-10.4 | 2005-12-14 | agreement | incoterms,fobcif,lic,ship | Y | Y | Y | Y |
| `trade-003.txt` | Agfeed Industries, Inc | EX-10.24 | 2009-12-17 | agreement | incoterms,fobcif,lcpay | Y | Y | Y | N |
| `trade-004.txt` | Allied Corp.  (ALID) | EX-10.2 | 2023-12-05 | agreement | incoterms,fobcif,lic | N | Y | Y | N |
| `trade-005.txt` | BALCHEM CORP  (BCPC) | EX-10.1 | 2007-03-21 | agreement | fobcif,cisg,ship | Y | Y | N | N |
| `trade-006.txt` | Bright Mountain Holdings, Inc./FL  | EX-10.10 | 2013-04-12 | agreement | fobcif,cisg,customs | N | N | Y | N |
| `trade-007.txt` | CEMENTOS PACASMAYO SAA  (CPAC) | EX-4.1 | 2013-04-30 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | Y |
| `trade-008.txt` | Canadian Solar Inc.  (CSIQ) | EX-4.4 | 2009-06-08 | agreement | incoterms,bol,port,fobcif | N | Y | Y | N |
| `trade-009.txt` | Canadian Solar Inc.  (CSIQ) | EX-4.5 | 2009-06-08 | agreement | incoterms,bol,port,fobcif | N | Y | Y | N |
| `trade-010.txt` | DATA I/O CORP  (DAIO) | EX-10 | 2016-11-14 | agreement | incoterms,fobcif,cisg | N | Y | N | Y |
| `trade-011.txt` | DRDGOLD LTD  (DRD, DRDGF) | EX-4.7 | 2023-10-30 | agreement | incoterms,fobcif,lic | Y | Y | N | Y |
| `trade-012.txt` | ELECTRAMECCANICA VEHICLES CORP. | EX-10.1 | 2016-10-12 | agreement | incoterms,fobcif,cisg | Y | Y | Y | N |
| `trade-013.txt` | EMULEX CORP /DE/ | EX-10.21 | 2003-09-24 | agreement | fobcif,customs,lic,ship | Y | Y | Y | N |
| `trade-014.txt` | EXELIXIS, INC.  (EXEL) | EX-10.42 | 2022-02-18 | amendment | incoterms,fobcif,ship | N | N | N | N |
| `trade-015.txt` | Enphase Energy, Inc.  (ENPH) | EX-10.4 | 2015-08-05 | amendment | incoterms,fobcif,customs | N | N | N | N |
| `trade-016.txt` | EnteroMedics Inc | EX-10.6 | 2012-08-08 | amendment | incoterms,fobcif,customs | N | N | N | N |
| `trade-017.txt` | Evraz North America Ltd | EX-10.3 | 2014-11-06 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-018.txt` | Evraz North America Ltd | EX-10.4 | 2014-11-06 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-019.txt` | Evraz North America plc | EX-10.6 | 2014-12-19 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-020.txt` | Evraz North America plc | EX-10.7 | 2014-12-19 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-021.txt` | FWF Holdings Inc. | EX-10.01 | 2015-05-19 | agreement | incoterms,fobcif,cisg,customs | N | N | Y | N |
| `trade-022.txt` | GLOBAL GOLD CORP | EX-10 | 2013-07-10 | amendment | bol,fobcif,customs,lic | N | N | Y | N |
| `trade-023.txt` | GOLD RESOURCE CORP  (GORO) | EX-10.3 | 2012-08-09 | agreement | incoterms,cisg,customs,lcpay | Y | N | Y | N |
| `trade-024.txt` | GOLD RESOURCE CORP  (GORO) | EX-10.5 | 2012-08-09 | agreement | incoterms,cisg,customs,lcpay | Y | N | Y | N |
| `trade-025.txt` | GRANT PRIDECO INC | EX-10.1 | 2007-11-09 | agreement | incoterms,bol,port,cisg | Y | Y | Y | N |
| `trade-026.txt` | HOKU SCIENTIFIC INC | EX-10.71 | 2008-06-06 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-027.txt` | HYDROGENICS CORP | EX-4.26 | 2002-06-26 | agreement | incoterms,fobcif,cisg | Y | Y | N | N |
| `trade-028.txt` | Homeland Security Network, Inc. | EX-10.1 | 2009-07-08 | agreement | bill_of_lading,port_load,fob_cif,cisg | N | N | Y | N |
| `trade-029.txt` | Imperium Renewables Inc | EX-10.11 | 2007-05-23 | agreement | incoterms,bol,port,fobcif | Y | N | Y | N |
| `trade-030.txt` | JinkoSolar Holding Co., Ltd.  (JKS | EX-10.33 | 2010-11-01 | agreement | incoterms,port,fobcif,lcpay | N | N | Y | N |
| `trade-031.txt` | JinkoSolar Holding Co., Ltd.  (JKS | EX-10.56 | 2010-05-12 | agreement | incoterms,bol,port,fobcif | N | N | Y | N |
| `trade-032.txt` | KEY ENERGY SERVICES INC | EX-10.1 | 2009-09-08 | agreement | incoterms,bol,port,fobcif | N | N | Y | N |
| `trade-033.txt` | KID CASTLE EDUCATIONAL CORP  (KDCE | EX-10.3 | 2008-03-31 | agreement | bill_of_lading,lc_pay,export_licence,shipment | Y | N | Y | N |
| `trade-034.txt` | Kallo Inc. | EX-10.33 | 2014-04-15 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-035.txt` | Kallo Inc. | EX-99.43A | 2020-12-23 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | N |
| `trade-036.txt` | LUNA INNOVATIONS INC  (LUNA) | EX-10.6 | 2006-11-13 | agreement | fobcif,cisg,lic | Y | Y | N | N |
| `trade-037.txt` | New Beginnings Acquisition Corp.   | EX-10.41 | 2021-06-21 | agreement | customs,lc_pay,export_licence | N | Y | Y | N |
| `trade-038.txt` | Novelis Inc. | EX-10.8 | 2004-12-20 | agreement | incoterms,bol,port,fobcif | N | N | Y | N |
| `trade-039.txt` | ON TRACK INNOVATIONS LTD | EX-10 | 2002-06-14 | agreement | fobcif,lcpay,lic | Y | Y | Y | N |
| `trade-040.txt` | Omrix Biopharmaceuticals, Inc. | EX-10.12 | 2006-01-18 | agreement | incoterms,fobcif,ship | Y | Y | Y | N |
| `trade-041.txt` | Prestige Brands Holdings, Inc.  (P | EX-10.1 | 2008-02-08 | agreement | incoterms,fobcif,ship | Y | Y | Y | N |
| `trade-042.txt` | Prestige Brands Holdings, Inc.  (P | EX-10.2 | 2008-02-08 | agreement | incoterms,fobcif,ship | Y | Y | Y | N |
| `trade-043.txt` | RADNOR HOLDINGS CORP | EX-10.1 | 2005-08-22 | amendment | incoterms,bol,fobcif,ship | Y | Y | N | N |
| `trade-044.txt` | Revance Therapeutics, Inc.  (RVNC) | EX-10.31 | 2021-02-25 | amendment | incoterms,fobcif,ship | N | N | N | N |
| `trade-045.txt` | SHUFFLE MASTER INC | EX-10.1 | 2005-09-16 | agreement | incoterms,fobcif,lcpay | Y | Y | Y | N |
| `trade-046.txt` | SPEIZMAN INDUSTRIES INC | EX-10.04 | 2001-09-28 | amendment | incoterms,bill_of_lading,fob_cif,lc_pay | N | N | Y | N |
| `trade-047.txt` | SPEIZMAN INDUSTRIES INC | EX-10.42 | 2002-09-27 | amendment | fobcif,cisg,lcpay,lic | N | Y | Y | N |
| `trade-048.txt` | SUNPOWER CORP  (SPWRQ) | EX-10.22 | 2005-10-11 | agreement | incoterms,fobcif,cisg | N | Y | Y | N |
| `trade-049.txt` | SUNVALLEY SOLAR, INC. | EX-10.7 | 2011-04-15 | agreement | incoterms,bol,port,fobcif | N | Y | Y | N |
| `trade-050.txt` | SUNVALLEY SOLAR, INC. | EX-99.1 | 2010-09-17 | agreement | incoterms,bol,port,fobcif | N | Y | Y | N |
| `trade-051.txt` | Solarfun Power Holdings Co., Ltd. | EX-10.33 | 2007-11-27 | agreement | incoterms,bol,port,fobcif | Y | Y | Y | Y |
| `trade-052.txt` | Spirit Airlines, Inc.  (SAVE) | EX-10.56 | 2024-02-09 | amendment | incoterms,fobcif,cisg,customs | N | Y | Y | N |
| `trade-053.txt` | Venture Global, Inc.  (VG) | EX-10.9 | 2026-05-12 | amendment | incoterms,fobcif,customs,ship | N | Y | Y | N |
| `trade-054.txt` | Voltaire Ltd. | EX-10.6 | 2007-07-10 | agreement | incoterms,fobcif,customs,lic | N | Y | N | N |
| `trade-055.txt` | WEST PHARMACEUTICAL SERVICES INC   | EX-10.1 | 2011-07-01 | agreement | incoterms,bol,fobcif,cisg | N | Y | Y | N |
| `trade-056.txt` | WEST PHARMACEUTICAL SERVICES INC   | EX-10.1 | 2014-08-15 | agreement | incoterms,bol,fobcif,cisg | N | Y | Y | N |
| `trade-057.txt` | WESTWATER RESOURCES, INC.  (WWR) | EX-10.1 | 2024-02-05 | agreement | incoterms,bol,fobcif,cisg | N | N | Y | N |
| `trade-058.txt` | XTENT INC | EX-10.10 | 2007-05-14 | agreement | incoterms,bol,fobcif,customs | Y | Y | Y | N |
| `trade-059.txt` | YINGLI GREEN ENERGY HOLDING CO LTD | EX-10.29 | 2007-06-04 | agreement | incoterms,fobcif,cisg | N | Y | Y | N |
| `trade-060.txt` | YINGLI GREEN ENERGY HOLDING CO LTD | EX-10.30 | 2007-06-04 | agreement | incoterms,fobcif,cisg | N | Y | Y | N |
| `trade-061.txt` | ZOLTEK COMPANIES INC | EX-10 | 2013-07-02 | agreement | incoterms,cisg,lic | Y | Y | Y | Y |
| `trade-062.txt` | ZOLTEK COMPANIES INC | EX-10.8 | 2013-05-02 | agreement | incoterms,cisg,lic | Y | N | Y | Y |

### 7-5. 국문 목록 (`kr-NNN.txt`, n=49)

전부 국가법령정보센터 · **표준서식** · KO · 저작권법 제7조제2호 → 재배포 가능.
무역여부 `xb`: 본문에 외자/수입/수출/신용장/선하증권/통관/Incoterms 등 신호 5회 이상.

| 파일 | 문서명 | 종류 | 소관 | xb | notices | amend | pay | email |
|---|---|---|---|:--:|:--:|:--:|:--:|:--:|
| `kr-001.txt` | (계약예규) 공사계약일반조건 | 계약예규 | 재정경제부 | N | Y | Y | Y | N |
| `kr-002.txt` | (계약예규) 물품구매(제조)계약일반조건 | 계약예규 | 재정경제부 | N | Y | Y | Y | N |
| `kr-003.txt` | (계약예규) 용역계약일반조건 | 계약예규 | 재정경제부 | N | Y | Y | Y | N |
| `kr-004.txt` | 건축공사 표준계약서 | 고시 | 국토교통부 | N | N | Y | Y | N |
| `kr-005.txt` | 건축물의 공사감리 표준계약서 | 고시 | 국토교통부 | N | Y | Y | Y | N |
| `kr-006.txt` | 건축물의 설계표준계약서 | 고시 | 국토교통부 | N | Y | Y | Y | N |
| `kr-007.txt` | 공공주택 건설기술(건설사업관리) 용역계약 특수조건 | 훈령 | 조달청 | N | N | Y | N | N |
| `kr-008.txt` | 공공주택 건설기술(설계) 용역계약 특수조건 | 훈령 | 조달청 | N | N | Y | N | N |
| `kr-009.txt` | 공사계약특수조건 | 지침 | 조달청 | N | N | Y | Y | N |
| `kr-010.txt` | 국가기관용 건설기술(건설사업관리) 용역계약 특수조건 | 지침 | 조달청 | N | N | Y | N | N |
| `kr-011.txt` | 국가기관용 건설기술(설계) 용역계약 특수조건 | 지침 | 조달청 | N | N | Y | N | N |
| `kr-012.txt` | 디지털서비스 카탈로그계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-013.txt` | 디지털콘텐츠 중개 표준약관 | 고시 | 과학기술정보통신부 | N | Y | Y | Y | N |
| `kr-014.txt` | 디지털콘텐츠 표준약관 | 고시 | 과학기술정보통신부 | N | Y | Y | Y | N |
| `kr-015.txt` | 디지털콘텐츠(영상) 공급표준계약서 | 고시 | 문화체육관광부 | N | Y | Y | Y | N |
| `kr-016.txt` | 디지털콘텐츠(음악) 공급표준계약서 | 고시 | 문화체육관광부 | N | Y | Y | Y | N |
| `kr-017.txt` | 레미콘 다수공급자계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-018.txt` | 물품 다수공급자계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-019.txt` | 물품 제조·구매 계약특수조건 표준(일반 및 방산) | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-020.txt` | 물품 제조·구매 계약특수조건 표준(특정조달) | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-021.txt` | 물품구매(제조)계약 특수조건 | 지침 | 조달청 | N | N | N | Y | N |
| `kr-022.txt` | 물품구매(제조)계약추가특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-023.txt` | 민간 국가유산수리 설계용역 표준계약서 | 고시 | 국가유산청 | N | Y | Y | Y | N |
| `kr-024.txt` | 민간 국가유산수리 표준도급계약서 | 고시 | 국가유산청 | N | N | N | Y | N |
| `kr-025.txt` | 상용소프트웨어 다수공급자계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-026.txt` | 상용소프트웨어 제3자단가계약 추가특수조건 | 지침 | 조달청 | N | N | Y | N | N |
| `kr-027.txt` | 시설대여(리스)계약 일반 조건 | 지침 | 조달청 | N | N | Y | Y | N |
| `kr-028.txt` | 아스콘 다수공급자계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-029.txt` | 외자계약일반조건(General Provisions for Foreign Contract) | 훈령 | 조달청 | Y | N | N | Y | N |
| `kr-030.txt` | 외주정비 계약특수조건 표준 | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-031.txt` | 용역 계약특수조건 표준 | 예규 | 방위사업청 | N | N | Y | Y | N |
| `kr-032.txt` | 용역 다수공급자계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-033.txt` | 용역 카탈로그계약 특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-034.txt` | 우수조달물품 임차계약 추가특수조건 | 공고 | 조달청 | N | N | N | N | N |
| `kr-035.txt` | 우주물체 제작 계약특수조건 표준 | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-036.txt` | 이러닝(전자학습) 이용표준약관 | 고시 | 산업통상부 | N | Y | Y | Y | N |
| `kr-037.txt` | 일괄입찰 등의 공사계약특수조건 | 지침 | 조달청 | N | Y | Y | Y | N |
| `kr-038.txt` | 일반무기체계 연구개발 계약특수조건 표준 | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-039.txt` | 일반용역계약특수조건 | 지침 | 조달청 | N | N | N | Y | N |
| `kr-040.txt` | 전자정부사업관리 위탁용역계약 특수조건 | 예규 | 행정안전부 | N | N | N | N | N |
| `kr-041.txt` | 조달청 공공주택 공사계약특수조건 | 훈령 | 조달청 | N | N | Y | Y | N |
| `kr-042.txt` | 조달청 군수품 구매(제조)계약 추가특수조건 | 지침 | 조달청 | N | N | N | N | N |
| `kr-043.txt` | 지방자치단체용 건설기술(건설사업관리) 용역계약 특수조건 | 지침 | 조달청 | N | N | Y | N | N |
| `kr-044.txt` | 지방자치단체용 건설기술(설계) 용역계약 특수조건 | 지침 | 조달청 | N | N | Y | N | N |
| `kr-045.txt` | 철근 다수공급자계약 추가특수조건 | 공고 | 조달청 | N | N | Y | N | N |
| `kr-046.txt` | 함정건조 계약특수조건 표준(일반 및 방산) | 예규 | 방위사업청 | Y | N | Y | Y | N |
| `kr-047.txt` | 혁신제품 시범구매계약 추가특수조건 | 지침 | 조달청 | N | N | N | Y | N |
| `kr-048.txt` | 혁신제품 제3자단가계약 추가특수조건 | 공고 | 조달청 | N | N | Y | Y | N |
| `kr-049.txt` | 화물자동차 운송사업 표준 위·수탁계약서 | 고시 | 국토교통부 | N | Y | Y | Y | N |

### 7-6. 접근 실패 / 라이선스로 배제한 소스

| 소스 | 결과 | 사유 |
|---|---|---|
| 공정거래위원회 표준하도급계약서 (59종) | **미수집** | 게시판 상세 페이지가 JS로 첨부파일 링크를 생성 — 정적 HTML에 hwp/hwpx/pdf 경로 없음. 우회하지 않고 중단 |
| DART (dart.fss.or.kr) 공시 첨부 | **미수집** | 검색 엔드포인트는 응답하나, 국문 주요계약 공시는 요약표 중심이고 계약서 전문 첨부가 희소. 실물 국문 확보 실패의 주원인 |
| 한국무역협회(KITA) 무역서식 | **배제** | 사이트 표기 `Copyright © KITA All rights reserved` — 재배포 불가. 다운로드 자체를 하지 않음 |
| 대한상사중재원(KCAB) 표준계약서 | **배제** | 목록 페이지가 "등록된 정보가 없습니다" + `Copyright ⓒ KCAB. All Rights Reserved` |
| ITC/UNCITRAL/ICC 모델계약 | **추가 수집 안 함** | 기존 9건이 이미 재배포 금지로 `.gitignore` 처리됨. 같은 사고 반복 회피 |
| 조달청 나라장터(g2b.go.kr) | **미수집** | 표준서식이 law.go.kr 계약예규·특수조건으로 이미 확보돼 중복 |

🟢 **재배포 불가로 격리한 파일: 0건.** 라이선스가 불명하거나 금지인 소스는 `_restricted/`에 넣지 않고 **애초에 내려받지 않았다** — 저장 전 확인 원칙 준수. 따라서 `.gitignore` 추가분도 없다.

### 7-7. 남은 한계

1. **실물 국문 계약서 0건** — 목표 20건은 표준서식으로 채웠다. 국문 *실물*의 조항 존재율은 여전히 미측정.
2. **국문 무역 전용은 사실상 1건** (`kr-029` 외자계약일반조건 — 조달청 국외조달, 제21조 대금결제에 취소불능 상업신용장). 국문 × 무역 교차 셀은 통계로 쓸 수 없다.
3. **국문 검출기는 영문 v4와 다른 코드다.** 존재율 차이의 일부가 검출기 차이일 가능성을 배제하지 못한다. 다만 두 검출기 모두 "메커니즘/구속력이 있어야 Y"라는 동일 기준으로 수기 감사를 거쳤다.
4. **무역 영문 62건 중 10건이 amendment/change order** — 완결된 계약서가 아니다. `doc_type` 열로 식별 가능하며, 제외한 52건 수치는 §7-3에 함께 실었다(결론 불변).

### 7-4. 🔴 검출기 확장 (2026-08-02) — 실물 수집 **전에** 고쳤다

국문 검출기가 `제12조(통지)` **괄호 규약만** 인식하고 있었다. 표준서식(계약예규)은 이 규약을
지키지만 **실물 계약서는 구획 방식이 제각각**이다. 실측:

| 형태 | 예시 | 확장 전 | 확장 후 |
|---|---|:---:|:---:|
| 괄호 (표준서식) | `제12조(통지)` | ✅ | ✅ |
| 대괄호 | `제12조 [통지]` | ❌ | ✅ |
| 공백 삽입 | `제 12 조 (통지)` | ❌ | ✅ |
| 마침표 | `제12조. 통지` | ❌ | ✅ |
| 낫표 | `제12조 「통지」` | ❌ | ✅ |
| 구획자 없음 | `제12조 통지` | ❌ | ✅ |
| 꺾쇠 | `【제12조】 통지` | ❌ | ✅ |
| 🔴 목차·번호목록 | `12. 통지` | ❌ | ❌ (의도적 배제) |

**8개 중 1개만 인식하고 있었다.** 이 상태로 실물을 재면 조항이 있어도 0%로 나오고,
"표준서식 vs 실물" 비교가 **검출기 인공물**이 된다 — 편향을 재려다 편향을 만드는 셈이다.

`조` 없는 `12. 통지`는 **일부러 넣지 않았다**. 목차·번호목록과 구별이 안 돼 오탐이 폭발한다.

🎯 **확장 후 기존 49건 재측정 결과가 완전히 동일하다** (notices 26.5% / amendment 83.7% /
payment 77.6% / contact 61.2% / email 0.0%). 표준서식이 전부 괄호 규약을 지키기 때문이다.
**기준선이 보존됐으므로 실물과의 비교가 유효하다** — 이걸 확인하지 않고 확장했으면
두 모집단의 차이가 검출기 변경 탓인지 실제 차이인지 구별할 수 없었다.
