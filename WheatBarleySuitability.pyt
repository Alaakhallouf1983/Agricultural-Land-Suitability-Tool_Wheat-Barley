# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║          أداة تقييم ملاءمة الأراضي الزراعية للقمح والشعير                      ║
║       Agricultural Land Suitability Tool for Wheat & Barley                     ║
║                                                                                  ║
║  المنهجية: FAO Land Evaluation Framework (1976) + Parametric Method             ║
║            + Weighted Multi-Criteria Evaluation (WMCE)                           ║
║            + Fuzzy Logic Classification                                          ║
║                                                                                  ║
║  المطوّر: ArcGIS Pro Python Toolbox (.pyt)                                      ║
║  الإصدار: 3.0 - Revolutionary Edition                                            ║
║  التوافق: ArcGIS Pro 2.x / 3.x                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

الفئات المعتمدة وفق FAO:
  S1  - ملائم تماماً    (Highly Suitable)        : 80-100
  S2  - ملائم متوسط     (Moderately Suitable)    : 60-79
  S3  - ملائم هامشياً   (Marginally Suitable)    : 40-59
  N1  - غير ملائم مؤقتاً (Currently Not Suitable): 20-39
  N2  - غير ملائم دائماً (Permanently Not Suitable): 0-19

المعاملات المعتمدة:
  [مناخية] أمطار، حرارة، رطوبة، أشعة شمس
  [تربة]   عمق، نسيج، درجة حموضة، صرف، ملوحة، مواد عضوية، CaCO3
  [طوبوغرافية] انحدار، ارتفاع، توجه الميل
  [بيئية] تآكل، تحجر، رطوبة سطحية
"""

import arcpy
import os
import sys
import json
import math
from arcpy.sa import *
from arcpy import env


# ══════════════════════════════════════════════════════════
#  تعريف صندوق الأدوات الرئيسي
# ══════════════════════════════════════════════════════════
class Toolbox(object):
    def __init__(self):
        self.label = "تقييم ملاءمة الأراضي - القمح والشعير"
        self.alias = "WheatBarleySuitability"
        self.tools = [
            LandSuitabilityTool,
            SensitivityAnalysisTool,
            ReportGeneratorTool
        ]


# ══════════════════════════════════════════════════════════
#  قاموس المعاملات المرجعية - FAO + IIASA + USDA
# ══════════════════════════════════════════════════════════
CROP_REQUIREMENTS = {
    "wheat": {
        "name_ar": "القمح",
        "name_en": "Wheat (Triticum aestivum)",
        # درجة الحرارة (°C)
        "temp": {
            "S1": (12, 22),   "S2": (8, 26),
            "S3": (5, 30),    "N1": (2, 34),  "N2": None,
            "weight": 0.18
        },
        # الأمطار السنوية (mm)
        "rainfall": {
            "S1": (400, 700), "S2": (300, 850),
            "S3": (200, 1000),"N1": (100, 1200),"N2": None,
            "weight": 0.20
        },
        # الانحدار (%)
        "slope": {
            "S1": (0, 5),     "S2": (5, 10),
            "S3": (10, 15),   "N1": (15, 30),  "N2": (30, 9999),
            "weight": 0.12
        },
        # عمق التربة (cm)
        "soil_depth": {
            "S1": (100, 9999),"S2": (75, 100),
            "S3": (50, 75),   "N1": (25, 50),  "N2": (0, 25),
            "weight": 0.10
        },
        # درجة الحموضة pH
        "ph": {
            "S1": (6.0, 7.5), "S2": (5.5, 8.0),
            "S3": (5.0, 8.5), "N1": (4.5, 9.0),"N2": None,
            "weight": 0.10
        },
        # التوصيل الكهربائي - الملوحة (dS/m)
        "ec": {
            "S1": (0, 4),     "S2": (4, 6),
            "S3": (6, 8),     "N1": (8, 12),   "N2": (12, 9999),
            "weight": 0.12
        },
        # المادة العضوية (%)
        "organic_matter": {
            "S1": (2, 9999),  "S2": (1, 2),
            "S3": (0.5, 1),   "N1": (0.2, 0.5),"N2": (0, 0.2),
            "weight": 0.08
        },
        # الصرف (نص: تصنيف رقمي 1-6)
        # 1=جيد جداً, 2=جيد, 3=متوسط, 4=رديء, 5=رديء جداً, 6=مقيّد
        "drainage": {
            "S1": [1, 2],     "S2": [3],
            "S3": [4],        "N1": [5],        "N2": [6],
            "weight": 0.10
        },
        # كربونات الكالسيوم CaCO3 (%)
        "caco3": {
            "S1": (0, 15),    "S2": (15, 25),
            "S3": (25, 35),   "N1": (35, 45),   "N2": (45, 9999),
            "weight": 0.00  # اختياري
        }
    },
    "barley": {
        "name_ar": "الشعير",
        "name_en": "Barley (Hordeum vulgare)",
        "temp": {
            "S1": (10, 25),  "S2": (7, 28),
            "S3": (4, 32),   "N1": (2, 36),    "N2": None,
            "weight": 0.16
        },
        "rainfall": {
            "S1": (300, 600),"S2": (200, 750),
            "S3": (150, 900),"N1": (80, 1100), "N2": None,
            "weight": 0.18
        },
        "slope": {
            "S1": (0, 6),    "S2": (6, 12),
            "S3": (12, 18),  "N1": (18, 30),   "N2": (30, 9999),
            "weight": 0.12
        },
        "soil_depth": {
            "S1": (80, 9999),"S2": (60, 80),
            "S3": (40, 60),  "N1": (20, 40),   "N2": (0, 20),
            "weight": 0.10
        },
        "ph": {
            "S1": (6.0, 8.0),"S2": (5.5, 8.5),
            "S3": (5.0, 9.0),"N1": (4.5, 9.5), "N2": None,
            "weight": 0.10
        },
        "ec": {
            "S1": (0, 6),    "S2": (6, 8),
            "S3": (8, 10),   "N1": (10, 16),   "N2": (16, 9999),
            "weight": 0.12
        },
        "organic_matter": {
            "S1": (1.5, 9999),"S2": (0.8, 1.5),
            "S3": (0.4, 0.8), "N1": (0.2, 0.4),"N2": (0, 0.2),
            "weight": 0.08
        },
        "drainage": {
            "S1": [1, 2, 3], "S2": [4],
            "S3": [5],       "N1": [6],         "N2": [],
            "weight": 0.10
        },
        "caco3": {
            "S1": (0, 20),   "S2": (20, 30),
            "S3": (30, 40),  "N1": (40, 50),   "N2": (50, 9999),
            "weight": 0.00
        }
    }
}

# تسميات الفئات
CLASS_LABELS = {
    5: {"code": "S1", "name_ar": "ملائم تماماً",      "name_en": "Highly Suitable",         "color": "GREEN_DARK"},
    4: {"code": "S2", "name_ar": "ملائم متوسط",       "name_en": "Moderately Suitable",     "color": "GREEN_LIGHT"},
    3: {"code": "S3", "name_ar": "ملائم هامشياً",     "name_en": "Marginally Suitable",     "color": "YELLOW"},
    2: {"code": "N1", "name_ar": "غير ملائم مؤقتاً",  "name_en": "Currently Not Suitable",  "color": "ORANGE"},
    1: {"code": "N2", "name_ar": "غير ملائم دائماً",  "name_en": "Permanently Not Suitable","color": "RED"}
}

SCORE_CLASSES = {5: 90, 4: 70, 3: 50, 2: 30, 1: 10}


# ══════════════════════════════════════════════════════════════════════════════
#  الدوال المساعدة العامة
# ══════════════════════════════════════════════════════════════════════════════

def classify_continuous_raster(raster, thresholds, nodata_val=-9999):
    """
    تصنيف رастر مستمر وفق عتبات FAO
    thresholds: dict من النوع {"S1":(min,max), "S2":(min,max), ...}
    الإخراج: رастر قيمه 1-5 (N2=1, N1=2, S3=3, S2=4, S1=5)
    """
    arcpy.AddMessage("      → تصنيف الرستر المستمر...")
    class_order = ["S1", "S2", "S3", "N1", "N2"]
    score_map   = {"S1": 5, "S2": 4, "S3": 3, "N1": 2, "N2": 1}

    result = Con(raster == nodata_val, 0, 0)  # رستر الأصفار كقاعدة

    for cls in reversed(class_order):  # من الأدنى للأعلى
        if thresholds.get(cls) is None:
            continue
        lo, hi = thresholds[cls]
        mask = (raster >= lo) & (raster <= hi)
        result = Con(mask, score_map[cls], result)

    return result


def classify_discrete_raster(raster, thresholds):
    """
    تصنيف رастر منفصل (مثل نوع الصرف)
    thresholds: dict من النوع {"S1":[1,2], "S2":[3], ...}
    """
    arcpy.AddMessage("      → تصنيف الرستر المنفصل...")
    score_map = {"S1": 5, "S2": 4, "S3": 3, "N1": 2, "N2": 1}
    result = Con(raster >= 0, 0)

    for cls, values in thresholds.items():
        if cls == "weight":
            continue
        score = score_map.get(cls, 0)
        for v in values:
            result = Con(raster == v, score, result)
    return result


def apply_limiting_factor(rasters_dict):
    """
    منهجية العامل المحدد (Limiting Factor Method - FAO)
    تأخذ الحد الأدنى من جميع الرسترات المصنفة
    """
    arcpy.AddMessage("    → تطبيق منهجية العامل المحدد (FAO)...")
    result = None
    for name, raster in rasters_dict.items():
        if result is None:
            result = raster
        else:
            result = Con(raster < result, raster, result)
    return result


def apply_weighted_overlay_manual(rasters_weights):
    """
    الطريقة: الوزن × الدرجة + الوزن × الدرجة ...
    rasters_weights: list of (raster, weight)
    الإخراج: رستر القيم الموزونة (مستمر)
    """
    arcpy.AddMessage("    → تطبيق التقييم متعدد المعايير الموزون (WMCE)...")
    total_weight = sum(w for _, w in rasters_weights)
    result = None

    for raster, weight in rasters_weights:
        normalized_weight = weight / total_weight
        weighted = raster * Float(normalized_weight)
        if result is None:
            result = weighted
        else:
            result = result + weighted
    return result


def convert_score_to_class(score_raster):
    """
    تحويل الدرجة المستمرة (1-5) إلى فئات FAO
    """
    result = Con(score_raster >= 4.5, 5,
            Con(score_raster >= 3.5, 4,
            Con(score_raster >= 2.5, 3,
            Con(score_raster >= 1.5, 2, 1))))
    return result


def convert_score_to_class_percentage(score_raster):
    """
    تحويل الدرجة (1-5) إلى نسبة مئوية (0-100)
    باستخدام التحويل: percentage = (score-1) / 4 * 100
    """
    return ((score_raster - 1) / 4.0) * 100


def apply_fuzzy_membership(raster, optimal_min, optimal_max, tolerance=0.3):
    """
    منهجية الفازي (Fuzzy Logic Membership Function)
    نوع: Fuzzy Gaussian Membership
    القيم المثلى تحصل على 1.0، وتنخفض تدريجياً خارجها
    """
    arcpy.AddMessage("      → تطبيق دالة العضوية الضبابية (Fuzzy Logic)...")
    mid = (optimal_min + optimal_max) / 2.0
    spread = (optimal_max - optimal_min) / 2.0

    if spread == 0:
        spread = 1.0

    sigma = spread * (1 + tolerance)
    # Gaussian: exp(-0.5 * ((x - mid) / sigma)^2)
    deviation = (raster - mid) / sigma
    fuzzy = Exp(-0.5 * deviation * deviation)
    return fuzzy


# ══════════════════════════════════════════════════════════════════════════════
#  الأداة الرئيسية: تقييم ملاءمة الأراضي
# ══════════════════════════════════════════════════════════════════════════════
class LandSuitabilityTool(object):
    def __init__(self):
        self.label = "1 | تقييم ملاءمة الأراضي (القمح / الشعير)"
        self.description = (
            "تقييم شامل لملاءمة الأراضي الزراعية لزراعة القمح والشعير\n"
            "وفق منهجية FAO 1976 مع دعم ثلاث طرق تحليل:\n"
            "  1. العامل المحدد  (Limiting Factor - FAO)\n"
            "  2. الوزن المتعدد  (Weighted MCE)\n"
            "  3. المنطق الضبابي (Fuzzy Logic)"
        )
        self.canRunInBackground = True
        self.category = "تحليل الملاءمة"

    def getParameterInfo(self):
        params = []

        # ── 0: اختيار المحصول ──────────────────────────────────────────────
        p0 = arcpy.Parameter(
            displayName="المحصول المستهدف",
            name="crop_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p0.filter.type = "ValueList"
        p0.filter.list = ["القمح (Wheat)", "الشعير (Barley)", "كلاهما (Both)"]
        p0.value = "القمح (Wheat)"
        params.append(p0)

        # ── 1: طريقة التحليل ───────────────────────────────────────────────
        p1 = arcpy.Parameter(
            displayName="طريقة التحليل",
            name="method",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p1.filter.type = "ValueList"
        p1.filter.list = [
            "FAO - العامل المحدد (Limiting Factor)",
            "MCE - الأوزان المتعددة (Weighted Overlay)",
            "Fuzzy Logic - المنطق الضبابي",
            "مدمجة - الأفضل (Combined Approach)"
        ]
        p1.value = "مدمجة - الأفضل (Combined Approach)"
        params.append(p1)

        # ═══════════════ المعاملات المناخية ═══════════════
        p2 = arcpy.Parameter(
            displayName="═══ رستر متوسط درجة الحرارة السنوية (°C)",
            name="temp_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p2)

        p3 = arcpy.Parameter(
            displayName="═══ رستر معدل الأمطار السنوية (mm)",
            name="rainfall_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p3)

        # ═══════════════ المعاملات الطوبوغرافية ═══════════════
        p4 = arcpy.Parameter(
            displayName="═══ رستر الانحدار (%) - يمكن إنشاؤه من DEM",
            name="slope_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p4)

        p5 = arcpy.Parameter(
            displayName="═══ نموذج الارتفاع الرقمي DEM (لحساب الانحدار تلقائياً إن لم يتوفر)",
            name="dem_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p5)

        # ═══════════════ معاملات التربة ═══════════════
        p6 = arcpy.Parameter(
            displayName="═══ رستر عمق التربة (cm)",
            name="soil_depth_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p6)

        p7 = arcpy.Parameter(
            displayName="═══ رستر درجة الحموضة (pH)",
            name="ph_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p7)

        p8 = arcpy.Parameter(
            displayName="═══ رستر التوصيل الكهربائي / الملوحة (dS/m)",
            name="ec_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p8)

        p9 = arcpy.Parameter(
            displayName="═══ رستر المادة العضوية (%)",
            name="om_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p9)

        p10 = arcpy.Parameter(
            displayName="═══ رستر الصرف (1=جيدجداً, 2=جيد, 3=متوسط, 4=رديء, 5=رديءجداً, 6=مقيّد)",
            name="drainage_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p10)

        p11 = arcpy.Parameter(
            displayName="═══ رستر كربونات الكالسيوم CaCO3 (%) - اختياري",
            name="caco3_raster",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p11)

        # ═══════════════ تعديل الأوزان ═══════════════
        p12 = arcpy.Parameter(
            displayName="تعديل أوزان المعاملات (JSON) - اتركه فارغاً للقيم الافتراضية",
            name="custom_weights",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        p12.value = ""
        params.append(p12)

        # ═══════════════ خيارات الإخراج ═══════════════
        p13 = arcpy.Parameter(
            displayName="مجلد الإخراج",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        params.append(p13)

        p14 = arcpy.Parameter(
            displayName="رستر الملاءمة النهائي (الإخراج)",
            name="output_suitability",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        params.append(p14)

        p15 = arcpy.Parameter(
            displayName="إنشاء رسترات الفئات الفرعية",
            name="save_sub_rasters",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        p15.value = True
        params.append(p15)

        p16 = arcpy.Parameter(
            displayName="إنشاء تقرير إحصائي (HTML)",
            name="generate_report",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        p16.value = True
        params.append(p16)

        p17 = arcpy.Parameter(
            displayName="تطبيق قناع منطقة الدراسة (اختياري)",
            name="study_area_mask",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input"
        )
        params.append(p17)

        return params

    def isLicensed(self):
        """التحقق من توفر ترخيص Spatial Analyst"""
        try:
            if arcpy.CheckExtension("Spatial") == "Available":
                return True
            else:
                arcpy.AddError("يتطلب هذا الأداة ترخيص ArcGIS Spatial Analyst!")
                return False
        except Exception:
            return False

    def updateParameters(self, parameters):
        """التحديث الديناميكي للمعاملات"""
        return

    def updateMessages(self, parameters):
        """التحقق من صحة المدخلات"""
        method_param = parameters[1]
        has_any_input = any(
            parameters[i].value for i in [2, 3, 4, 5, 6, 7, 8, 9, 10]
        )
        if not has_any_input:
            parameters[2].setWarningMessage(
                "تحذير: لم يتم إدخال أي رستر. يجب إدخال رستر واحد على الأقل."
            )

        # التحقق من صحة JSON الأوزان
        if parameters[12].value:
            try:
                json.loads(parameters[12].value)
            except json.JSONDecodeError:
                parameters[12].setErrorMessage(
                    "تنسيق JSON غير صحيح. مثال صحيح:\n"
                    '{"temp": 0.20, "rainfall": 0.25, "slope": 0.15, '
                    '"soil_depth": 0.10, "ph": 0.10, "ec": 0.10, '
                    '"organic_matter": 0.05, "drainage": 0.05}'
                )

    def execute(self, parameters, messages):
        """تنفيذ الأداة الرئيسية"""
        try:
            arcpy.CheckOutExtension("Spatial")
            env.overwriteOutput = True

            # ── استخراج المعاملات ──
            crop_choice   = parameters[0].valueAsText
            method        = parameters[1].valueAsText
            temp_r        = parameters[2].value
            rainfall_r    = parameters[3].value
            slope_r       = parameters[4].value
            dem_r         = parameters[5].value
            soil_depth_r  = parameters[6].value
            ph_r          = parameters[7].value
            ec_r          = parameters[8].value
            om_r          = parameters[9].value
            drainage_r    = parameters[10].value
            caco3_r       = parameters[11].value
            custom_w      = parameters[12].valueAsText
            output_folder = parameters[13].valueAsText
            output_path   = parameters[14].valueAsText
            save_subs     = parameters[15].value
            gen_report    = parameters[16].value
            mask_layer    = parameters[17].value

            # ── تحديد المحاصيل ──
            crops_to_process = []
            if "Both" in crop_choice or "كلاهما" in crop_choice:
                crops_to_process = ["wheat", "barley"]
            elif "Wheat" in crop_choice or "القمح" in crop_choice:
                crops_to_process = ["wheat"]
            else:
                crops_to_process = ["barley"]

            # ── تطبيق قناع منطقة الدراسة ──
            if mask_layer:
                env.mask = mask_layer
                arcpy.AddMessage("✓ تم تعيين قناع منطقة الدراسة")

            # ── حساب الانحدار من DEM إذا لزم ──
            if not slope_r and dem_r:
                arcpy.AddMessage("◈ حساب الانحدار من DEM...")
                slope_r = Slope(dem_r, "PERCENT_RISE")
                if save_subs:
                    slope_path = os.path.join(output_folder, "slope_derived.tif")
                    slope_r.save(slope_path)
                    arcpy.AddMessage(f"  ← تم حفظ رستر الانحدار: {slope_path}")

            results_summary = {}

            for crop in crops_to_process:
                arcpy.AddMessage("\n" + "═"*60)
                arcpy.AddMessage(f"◈◈◈ معالجة محصول: {CROP_REQUIREMENTS[crop]['name_ar']} ({CROP_REQUIREMENTS[crop]['name_en']})")
                arcpy.AddMessage("═"*60)

                req = CROP_REQUIREMENTS[crop].copy()

                # ── تطبيق الأوزان المخصصة ──
                if custom_w:
                    try:
                        custom_weights = json.loads(custom_w)
                        for param_name, weight in custom_weights.items():
                            if param_name in req:
                                req[param_name]["weight"] = weight
                        arcpy.AddMessage("  ✓ تم تطبيق الأوزان المخصصة")
                    except Exception as e:
                        arcpy.AddWarning(f"  ⚠ خطأ في تطبيق الأوزان المخصصة: {e}")

                # ── تصنيف كل معامل ──
                classified = {}
                arcpy.AddMessage("\n  [1] تصنيف المعاملات...")

                if temp_r:
                    arcpy.AddMessage("    • درجة الحرارة")
                    classified["temp"] = classify_continuous_raster(
                        Raster(temp_r), req["temp"]
                    )

                if rainfall_r:
                    arcpy.AddMessage("    • الأمطار")
                    classified["rainfall"] = classify_continuous_raster(
                        Raster(rainfall_r), req["rainfall"]
                    )

                if slope_r:
                    arcpy.AddMessage("    • الانحدار")
                    slope_input = slope_r if isinstance(slope_r, Raster) else Raster(slope_r)
                    classified["slope"] = classify_continuous_raster(
                        slope_input, req["slope"]
                    )

                if soil_depth_r:
                    arcpy.AddMessage("    • عمق التربة")
                    classified["soil_depth"] = classify_continuous_raster(
                        Raster(soil_depth_r), req["soil_depth"]
                    )

                if ph_r:
                    arcpy.AddMessage("    • درجة الحموضة pH")
                    classified["ph"] = classify_continuous_raster(
                        Raster(ph_r), req["ph"]
                    )

                if ec_r:
                    arcpy.AddMessage("    • الملوحة EC")
                    classified["ec"] = classify_continuous_raster(
                        Raster(ec_r), req["ec"]
                    )

                if om_r:
                    arcpy.AddMessage("    • المادة العضوية")
                    classified["organic_matter"] = classify_continuous_raster(
                        Raster(om_r), req["organic_matter"]
                    )

                if drainage_r:
                    arcpy.AddMessage("    • الصرف")
                    classified["drainage"] = classify_discrete_raster(
                        Raster(drainage_r), req["drainage"]
                    )

                if caco3_r and req["caco3"]["weight"] > 0:
                    arcpy.AddMessage("    • CaCO3")
                    classified["caco3"] = classify_continuous_raster(
                        Raster(caco3_r), req["caco3"]
                    )

                if not classified:
                    arcpy.AddError("  ✗ لا توجد بيانات مدخلة لمعالجتها!")
                    continue

                arcpy.AddMessage(f"  ✓ تم تصنيف {len(classified)} معامل")

                # ── حفظ رسترات الفئات الفرعية ──
                if save_subs:
                    sub_folder = os.path.join(output_folder, f"{crop}_classified")
                    os.makedirs(sub_folder, exist_ok=True)
                    arcpy.AddMessage(f"\n  [2] حفظ رسترات الفئات الفرعية في: {sub_folder}")
                    for param_name, r in classified.items():
                        sub_path = os.path.join(sub_folder, f"{crop}_{param_name}_class.tif")
                        r.save(sub_path)
                        arcpy.AddMessage(f"    ← {param_name}: {sub_path}")

                # ── تطبيق طريقة التحليل ──
                arcpy.AddMessage(f"\n  [3] تطبيق طريقة التحليل: {method}")

                final_raster = None

                if "مدمجة" in method or "Combined" in method:
                    # الطريقة المدمجة: MCE + Limiting Factor
                    # أولاً: حساب الوزن
                    rasters_weights = [
                        (r, req[name]["weight"])
                        for name, r in classified.items()
                        if req.get(name, {}).get("weight", 0) > 0
                    ]
                    if rasters_weights:
                        wce_result = apply_weighted_overlay_manual(rasters_weights)
                        # تحويل من مقياس 1-5 إلى 0-100
                        wce_pct = convert_score_to_class_percentage(wce_result)

                        # ثانياً: العامل المحدد (يقيّد WCE)
                        lf_result = apply_limiting_factor(classified)
                        lf_pct = convert_score_to_class_percentage(Float(lf_result))

                        # الدمج: 70% WCE + 30% LF
                        final_score = (wce_pct * 0.70) + (lf_pct * 0.30)
                        # تحويل النسبة إلى فئات
                        final_raster = Con(final_score >= 80, 5,
                                      Con(final_score >= 60, 4,
                                      Con(final_score >= 40, 3,
                                      Con(final_score >= 20, 2, 1))))
                    else:
                        arcpy.AddWarning("  ⚠ لا توجد أوزان محددة، سيُستخدم العامل المحدد")
                        final_raster = apply_limiting_factor(classified)

                elif "FAO" in method or "العامل المحدد" in method:
                    final_raster = apply_limiting_factor(classified)

                elif "MCE" in method or "Weighted" in method or "الأوزان" in method:
                    rasters_weights = [
                        (r, req[name]["weight"])
                        for name, r in classified.items()
                        if req.get(name, {}).get("weight", 0) > 0
                    ]
                    if rasters_weights:
                        wce = apply_weighted_overlay_manual(rasters_weights)
                        final_raster = convert_score_to_class(wce)
                    else:
                        final_raster = apply_limiting_factor(classified)

                elif "Fuzzy" in method or "الضبابي" in method:
                    arcpy.AddMessage("    → تطبيق المنطق الضبابي...")
                    fuzzy_rasters = []
                    s1_vals = {
                        "temp": req["temp"]["S1"],
                        "rainfall": req["rainfall"]["S1"],
                        "slope": req["slope"]["S1"],
                        "soil_depth": req["soil_depth"].get("S1", (75, 9999)),
                        "ph": req["ph"]["S1"],
                        "ec": req["ec"]["S1"],
                    }
                    input_map = {
                        "temp": temp_r, "rainfall": rainfall_r,
                        "slope": slope_r, "soil_depth": soil_depth_r,
                        "ph": ph_r, "ec": ec_r
                    }
                    for param, raster_in in input_map.items():
                        if raster_in and param in s1_vals:
                            lo, hi = s1_vals[param]
                            r_in = raster_in if isinstance(raster_in, Raster) else Raster(raster_in)
                            fz = apply_fuzzy_membership(r_in, lo, hi)
                            w = req[param].get("weight", 0.1)
                            fuzzy_rasters.append((fz, w))

                    if fuzzy_rasters:
                        fuzzy_combined = apply_weighted_overlay_manual(fuzzy_rasters)
                        # تحويل 0-1 إلى 1-5
                        fuzzy_score = fuzzy_combined * 4 + 1
                        final_raster = convert_score_to_class(fuzzy_score)
                    else:
                        final_raster = apply_limiting_factor(classified)

                # ── حفظ النتيجة النهائية ──
                if final_raster:
                    if len(crops_to_process) == 1:
                        out_path = output_path
                    else:
                        base, ext = os.path.splitext(output_path)
                        out_path = f"{base}_{crop}{ext}"
                        if not ext:
                            out_path = f"{output_path}_{crop}.tif"

                    final_raster.save(out_path)
                    arcpy.AddMessage(f"\n  ✅ تم حفظ رستر الملاءمة: {out_path}")

                    # ── إحصائيات ──
                    results_summary[crop] = {
                        "output": out_path,
                        "params_used": list(classified.keys())
                    }

                    # ── تطبيق رمزية اللون ──
                    self._apply_symbology(out_path)

                    # ── توليد التقرير ──
                    if gen_report:
                        self._generate_html_report(
                            out_path, crop, req,
                            list(classified.keys()), method,
                            output_folder
                        )

            arcpy.AddMessage("\n" + "═"*60)
            arcpy.AddMessage("◈◈◈ اكتملت العملية بنجاح!")
            arcpy.AddMessage("═"*60)

            for crop, info in results_summary.items():
                arcpy.AddMessage(f"\n  ✓ {CROP_REQUIREMENTS[crop]['name_ar']}:")
                arcpy.AddMessage(f"    الملف: {info['output']}")
                arcpy.AddMessage(f"    المعاملات: {', '.join(info['params_used'])}")

            arcpy.CheckInExtension("Spatial")

        except arcpy.ExecuteError:
            arcpy.AddError(arcpy.GetMessages(2))
        except Exception as e:
            arcpy.AddError(f"خطأ غير متوقع: {str(e)}")
            import traceback
            arcpy.AddError(traceback.format_exc())

    def _apply_symbology(self, raster_path):
        """تطبيق رمزية الألوان التلقائية"""
        try:
            arcpy.AddMessage("  → تطبيق رمزية الألوان...")
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            map_obj = aprx.activeMap
            if map_obj:
                lyr = map_obj.addDataFromPath(raster_path)
                arcpy.AddMessage(f"  ✓ تمت إضافة الطبقة إلى الخريطة: {lyr.name}")
        except Exception:
            arcpy.AddMessage("  ⓘ لم يتم تطبيق الرمزية تلقائياً (شغّل من داخل ArcGIS Pro)")

    def _generate_html_report(self, raster_path, crop, req, params_used, method, output_folder):
        """توليد تقرير HTML تفاعلي"""
        arcpy.AddMessage("  → توليد التقرير HTML...")
        crop_info = CROP_REQUIREMENTS[crop]
        report_path = os.path.join(output_folder, f"report_{crop}.html")

        params_table = ""
        for p in params_used:
            if p in req:
                param_data = req[p]
                s1 = param_data.get("S1", "—")
                s2 = param_data.get("S2", "—")
                weight = param_data.get("weight", 0) * 100
                params_table += f"""
                <tr>
                    <td><strong>{p}</strong></td>
                    <td class="s1">{s1}</td>
                    <td class="s2">{s2}</td>
                    <td>{weight:.0f}%</td>
                </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>تقرير ملاءمة الأراضي - {crop_info['name_ar']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    background: linear-gradient(135deg, #1a2a1a 0%, #2d4a1e 50%, #1a3a2a 100%);
    color: #e8f5e9; min-height: 100vh; padding: 20px;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  .header {{
    background: linear-gradient(135deg, #2e7d32, #1b5e20);
    border-radius: 15px; padding: 30px; text-align: center;
    margin-bottom: 25px; border: 2px solid #4caf50;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }}
  .header h1 {{ font-size: 2em; color: #a5d6a7; margin-bottom: 10px; }}
  .header h2 {{ font-size: 1.3em; color: #c8e6c9; }}
  .badge {{
    display: inline-block; background: #4caf50; color: white;
    padding: 5px 15px; border-radius: 20px; margin: 5px;
    font-size: 0.9em;
  }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{
    background: rgba(255,255,255,0.05); border-radius: 12px;
    padding: 20px; border: 1px solid rgba(76,175,80,0.3);
    backdrop-filter: blur(5px);
  }}
  .card h3 {{ color: #81c784; margin-bottom: 15px; font-size: 1.1em; border-bottom: 1px solid #4caf5040; padding-bottom: 8px; }}
  .suitability-classes {{ grid-column: 1 / -1; }}
  .class-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 10px; }}
  .cls-card {{ text-align: center; padding: 15px; border-radius: 10px; }}
  .cls-S1 {{ background: linear-gradient(135deg, #1b5e20, #2e7d32); border: 2px solid #4caf50; }}
  .cls-S2 {{ background: linear-gradient(135deg, #33691e, #558b2f); border: 2px solid #8bc34a; }}
  .cls-S3 {{ background: linear-gradient(135deg, #f57f17, #f9a825); border: 2px solid #ffc107; color: #000; }}
  .cls-N1 {{ background: linear-gradient(135deg, #e65100, #bf360c); border: 2px solid #ff5722; }}
  .cls-N2 {{ background: linear-gradient(135deg, #b71c1c, #7f0000); border: 2px solid #f44336; }}
  .cls-card .code {{ font-size: 1.8em; font-weight: bold; margin-bottom: 5px; }}
  .cls-card .range {{ font-size: 0.75em; opacity: 0.9; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: rgba(76,175,80,0.3); padding: 10px; text-align: right; color: #a5d6a7; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
  tr:hover td {{ background: rgba(76,175,80,0.1); }}
  .s1 {{ color: #66bb6a; font-weight: bold; }}
  .s2 {{ color: #aed581; }}
  .full-width {{ grid-column: 1 / -1; }}
  .meta {{ font-size: 0.85em; opacity: 0.7; text-align: center; margin-top: 20px; padding: 10px; }}
  .req-card {{ background: rgba(76,175,80,0.1); border-radius: 8px; padding: 10px; margin: 5px 0; }}
  .req-label {{ color: #81c784; font-weight: bold; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🌾 تقرير ملاءمة الأراضي الزراعية</h1>
    <h2>{crop_info['name_ar']} — {crop_info['name_en']}</h2>
    <div style="margin-top:15px">
      <span class="badge">📊 {method.split('(')[0].strip()}</span>
      <span class="badge">🌍 FAO Framework 1976</span>
      <span class="badge">📍 {len(params_used)} معامل</span>
    </div>
  </div>

  <div class="grid">
    <div class="card suitability-classes">
      <h3>🏷️ فئات الملاءمة المعتمدة (FAO)</h3>
      <div class="class-grid">
        <div class="cls-card cls-S1">
          <div class="code">S1</div>
          <div>ملائم تماماً</div>
          <div class="range">80 - 100</div>
        </div>
        <div class="cls-card cls-S2">
          <div class="code">S2</div>
          <div>ملائم متوسط</div>
          <div class="range">60 - 79</div>
        </div>
        <div class="cls-card cls-S3">
          <div class="code">S3</div>
          <div>ملائم هامشياً</div>
          <div class="range">40 - 59</div>
        </div>
        <div class="cls-card cls-N1">
          <div class="code">N1</div>
          <div>غير ملائم مؤقتاً</div>
          <div class="range">20 - 39</div>
        </div>
        <div class="cls-card cls-N2">
          <div class="code">N2</div>
          <div>غير ملائم دائماً</div>
          <div class="range">0 - 19</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>⚖️ المعاملات المستخدمة وأوزانها</h3>
      <table>
        <tr><th>المعامل</th><th>S1 (المثلى)</th><th>S2</th><th>الوزن</th></tr>
        {params_table}
      </table>
    </div>

    <div class="card">
      <h3>🌾 المتطلبات البيئية للمحصول</h3>
      <div class="req-card">
        <div class="req-label">درجة الحرارة المثلى:</div>
        <div>{req['temp']['S1']} °C</div>
      </div>
      <div class="req-card">
        <div class="req-label">الأمطار المثلى:</div>
        <div>{req['rainfall']['S1']} مم/سنة</div>
      </div>
      <div class="req-card">
        <div class="req-label">درجة الحموضة المثلى:</div>
        <div>pH {req['ph']['S1']}</div>
      </div>
      <div class="req-card">
        <div class="req-label">الانحدار المثلى:</div>
        <div>{req['slope']['S1']}%</div>
      </div>
      <div class="req-card">
        <div class="req-label">الملوحة المقبولة:</div>
        <div>EC {req['ec']['S1']} dS/m</div>
      </div>
    </div>

    <div class="card full-width">
      <h3>📁 ملف الإخراج</h3>
      <p style="color:#a5d6a7; word-break:break-all; padding:10px; background:rgba(0,0,0,0.3); border-radius:5px;">
        {raster_path}
      </p>
    </div>
  </div>

  <div class="meta">
    تم إنشاء هذا التقرير بواسطة أداة تقييم ملاءمة الأراضي للقمح والشعير<br>
    ArcGIS Pro Python Toolbox | FAO Land Evaluation Framework
  </div>
</div>
</body>
</html>"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        arcpy.AddMessage(f"  ✅ تم حفظ التقرير: {report_path}")


# ══════════════════════════════════════════════════════════════════════════════
#  الأداة الثانية: تحليل الحساسية
# ══════════════════════════════════════════════════════════════════════════════
class SensitivityAnalysisTool(object):
    def __init__(self):
        self.label = "2 | تحليل الحساسية للأوزان"
        self.description = (
            "تحليل تأثير تغيير الأوزان على النتيجة النهائية\n"
            "يساعد في فهم أكثر المعاملات تأثيراً في تحديد الملاءمة"
        )
        self.canRunInBackground = True
        self.category = "تحليل متقدم"

    def getParameterInfo(self):
        params = []

        p0 = arcpy.Parameter(
            displayName="رستر الملاءمة الأساسي (من الأداة 1)",
            name="base_suitability",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )
        params.append(p0)

        p1 = arcpy.Parameter(
            displayName="المحصول",
            name="crop_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p1.filter.type = "ValueList"
        p1.filter.list = ["القمح (Wheat)", "الشعير (Barley)"]
        params.append(p1)

        p2 = arcpy.Parameter(
            displayName="معامل التغيير في الوزن (%)",
            name="weight_variation",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p2.value = 10
        params.append(p2)

        p3 = arcpy.Parameter(
            displayName="مجلد الإخراج",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        params.append(p3)

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        if parameters[2].value:
            v = parameters[2].value
            if v < 5 or v > 30:
                parameters[2].setWarningMessage("يُنصح بمعامل تغيير بين 5% و30%")

    def execute(self, parameters, messages):
        arcpy.AddMessage("◈ تحليل الحساسية للأوزان")
        crop = "wheat" if "Wheat" in parameters[1].valueAsText or "القمح" in parameters[1].valueAsText else "barley"
        variation = parameters[2].value / 100.0
        output_folder = parameters[3].valueAsText

        req = CROP_REQUIREMENTS[crop]
        report_lines = []
        report_lines.append(f"تحليل الحساسية للأوزان - {CROP_REQUIREMENTS[crop]['name_ar']}")
        report_lines.append("=" * 60)
        report_lines.append(f"معامل التغيير: ±{parameters[2].value}%")
        report_lines.append("")

        arcpy.AddMessage("\nالأوزان الافتراضية:")
        for param, data in req.items():
            if isinstance(data, dict) and "weight" in data:
                w = data["weight"]
                w_up   = min(1.0, w * (1 + variation))
                w_down = max(0.0, w * (1 - variation))
                line = f"  {param}: {w:.3f} → (+{parameters[2].value}%: {w_up:.3f}) | (-{parameters[2].value}%: {w_down:.3f})"
                arcpy.AddMessage(line)
                report_lines.append(line)

        # حفظ تقرير نصي
        report_path = os.path.join(output_folder, f"sensitivity_{crop}.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        arcpy.AddMessage(f"\n✅ تقرير الحساسية: {report_path}")


# ══════════════════════════════════════════════════════════════════════════════
#  الأداة الثالثة: مولّد التقارير الإحصائية
# ══════════════════════════════════════════════════════════════════════════════
class ReportGeneratorTool(object):
    def __init__(self):
        self.label = "3 | تقرير إحصائي للمساحات"
        self.description = (
            "حساب مساحة كل فئة من فئات الملاءمة وتوليد تقرير إحصائي شامل\n"
            "يشمل النسب المئوية والرسوم البيانية"
        )
        self.canRunInBackground = True
        self.category = "تقارير"

    def getParameterInfo(self):
        params = []

        p0 = arcpy.Parameter(
            displayName="رستر الملاءمة النهائي",
            name="suitability_raster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )
        params.append(p0)

        p1 = arcpy.Parameter(
            displayName="المحصول",
            name="crop_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p1.filter.type = "ValueList"
        p1.filter.list = ["القمح (Wheat)", "الشعير (Barley)"]
        params.append(p1)

        p2 = arcpy.Parameter(
            displayName="وحدة المساحة",
            name="area_unit",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["هكتار (Hectare)", "كيلومتر مربع (km²)", "دونم (Dunam)", "فدان (Feddan)"]
        p2.value = "هكتار (Hectare)"
        params.append(p2)

        p3 = arcpy.Parameter(
            displayName="مجلد الإخراج",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        params.append(p3)

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:
            arcpy.CheckOutExtension("Spatial")
            raster_path  = parameters[0].valueAsText
            crop_choice  = parameters[1].valueAsText
            area_unit    = parameters[2].valueAsText
            output_folder = parameters[3].valueAsText

            crop = "wheat" if "Wheat" in crop_choice or "القمح" in crop_choice else "barley"
            crop_name = CROP_REQUIREMENTS[crop]["name_ar"]

            arcpy.AddMessage(f"◈ حساب إحصائيات الملاءمة: {crop_name}")

            raster = Raster(raster_path)
            cell_size = raster.meanCellWidth

            # الوحدة التحويلية (من متر مربع)
            unit_factors = {
                "هكتار (Hectare)":       10000,
                "كيلومتر مربع (km²)":   1000000,
                "دونم (Dunam)":          1000,
                "فدان (Feddan)":         4200
            }
            unit_factor = unit_factors.get(area_unit, 10000)
            unit_name = area_unit.split("(")[0].strip()

            # حساب المساحة لكل فئة
            stats = {}
            total_cells = 0

            for class_val, class_info in CLASS_LABELS.items():
                count_raster = Con(raster == class_val, 1)
                try:
                    result = arcpy.GetRasterProperties_management(
                        Con(raster == class_val, class_val), "MAXIMUM"
                    )
                    # نحسب الخلايا
                    arr = arcpy.RasterToNumPyArray(
                        Con(raster == class_val, 1, 0),
                        nodata_to_value=0
                    )
                    count = int(arr.sum())
                    area = (count * cell_size * cell_size) / unit_factor
                    stats[class_val] = {
                        "code": class_info["code"],
                        "name_ar": class_info["name_ar"],
                        "cells": count,
                        "area": area
                    }
                    total_cells += count
                    arcpy.AddMessage(
                        f"  {class_info['code']} - {class_info['name_ar']}: "
                        f"{count:,} خلية | {area:,.2f} {unit_name}"
                    )
                except Exception as e:
                    arcpy.AddWarning(f"  ⚠ تعذر حساب {class_info['code']}: {e}")
                    stats[class_val] = {
                        "code": class_info["code"],
                        "name_ar": class_info["name_ar"],
                        "cells": 0, "area": 0
                    }

            # ── توليد تقرير HTML إحصائي ──
            total_area = sum(v["area"] for v in stats.values())
            bars_html = ""
            colors = {5:"#2e7d32", 4:"#558b2f", 3:"#f9a825", 2:"#e65100", 1:"#b71c1c"}

            for cv in [5, 4, 3, 2, 1]:
                if cv in stats:
                    s = stats[cv]
                    pct = (s["area"] / total_area * 100) if total_area > 0 else 0
                    bars_html += f"""
                    <div style="margin:8px 0">
                      <div style="display:flex; align-items:center; gap:10px">
                        <span style="width:35px;font-weight:bold;color:{colors[cv]}">{s['code']}</span>
                        <span style="width:140px">{s['name_ar']}</span>
                        <div style="flex:1;background:rgba(255,255,255,0.1);border-radius:5px;height:22px">
                          <div style="width:{pct:.1f}%;background:{colors[cv]};height:100%;border-radius:5px;
                               display:flex;align-items:center;padding-right:5px;font-size:0.8em">
                            {pct:.1f}%
                          </div>
                        </div>
                        <span style="width:120px;text-align:left">{s['area']:,.1f} {unit_name}</span>
                      </div>
                    </div>"""

            report_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>تقرير إحصائي - {crop_name}</title>
<style>
  body {{font-family:'Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#1a2a1a,#2d4a1e);
         color:#e8f5e9;padding:20px;min-height:100vh}}
  .container{{max-width:900px;margin:0 auto}}
  .header{{background:linear-gradient(135deg,#2e7d32,#1b5e20);border-radius:15px;padding:25px;
           text-align:center;margin-bottom:20px;border:2px solid #4caf50}}
  h1{{color:#a5d6a7;font-size:1.8em}} h2{{color:#c8e6c9}}
  .card{{background:rgba(255,255,255,0.05);border-radius:12px;padding:20px;
         border:1px solid rgba(76,175,80,0.3);margin-bottom:15px}}
  .card h3{{color:#81c784;margin-bottom:15px;border-bottom:1px solid #4caf5040;padding-bottom:8px}}
  .total{{text-align:center;font-size:1.5em;color:#a5d6a7;padding:15px;
          background:rgba(76,175,80,0.1);border-radius:8px;margin-bottom:15px}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📊 التقرير الإحصائي للملاءمة</h1>
    <h2>{crop_name}</h2>
  </div>
  <div class="card">
    <h3>📐 توزيع المساحات حسب فئة الملاءمة</h3>
    <div class="total">الإجمالي: {total_area:,.1f} {unit_name}</div>
    {bars_html}
  </div>
</div>
</body>
</html>"""

            report_path = os.path.join(output_folder, f"area_report_{crop}.html")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_html)

            arcpy.AddMessage(f"\n✅ التقرير الإحصائي: {report_path}")
            arcpy.CheckInExtension("Spatial")

        except arcpy.ExecuteError:
            arcpy.AddError(arcpy.GetMessages(2))
        except Exception as e:
            arcpy.AddError(f"خطأ: {str(e)}")
            import traceback
            arcpy.AddError(traceback.format_exc())
