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
