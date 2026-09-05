# -*- coding: utf-8 -*-
"""
modules/module9_operations_report.py
───────────────────────────────────
نظام مركز تقارير العمليات (Operations Reporting System):
- الربط بين ملف المحفظة وملف السدادات / التحصيل عن طريق [رقم المديونية]
- حساب التغطية بناءً على [تاريخ المتابعة] في المحفظة وفق الفترة الزمنية (يومي / أسبوعي / شهري)
- حساب التحصيل بناءً على [مبلغ السداد] في ملف السدادات
- حساب نسب التغطية ونسب التحصيل مقارنة بالمستهدفات
- جدول التقرير التنفيذي:
  المشرف | المحصل | التغطية | مستهدف التغطية | نسبة التغطية % | التحصيل | مستهدف التحصيل | نسبة التحصيل %
"""

from __future__ import annotations
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import polars as pl

_log = logging.getLogger("STC_OPS")

_DEBT_COLS          = ["رقم المديونية", "رقم المديونيه", "رقم العقد", "رقم الحساب", "المديونية", "debt_id", "Debt ID"]
_ID_COLS            = ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "ID", "customer_id"]
_SUPERVISOR_COLS     = ["المشرف", "اسم المشرف", "supervisor", "Supervisor"]
_COLLECTOR_COLS      = ["المحصل", "اسم المحصل", "الموظف", "محصل", "collector", "Collector"]
_FOLLOWUP_DATE_COLS  = ["تاريخ المتابعة", "تاريخ اخر متابعة", "آخر متابعة للعميل", "المتابعة", "تاريخ المتابعه", "followup_date", "Followup Date"]
_PAYMENT_AMOUNT_COLS = ["مبلغ السداد", "قيمة السداد", "المبلغ", "amount", "Amount", "paid_amount", "السدادات الموثقة"]
_PAYMENT_DATE_COLS   = ["تاريخ السداد", "تاريخ الدفع", "تاريخ الحركة", "تاريخ العملية", "التاريخ", "date", "Date", "payment_date"]


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    if df is None or len(df.columns) == 0:
        return None
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        for cand in candidates:
            if cand.strip().lower() in c.strip().lower() or c.strip().lower() in cand.strip().lower():
                return c
    return None


def _clean_str_id(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _clean_float_val(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).replace(",", "").replace(" ", "").replace("﷼", "").strip()
        return float(s) if s else 0.0
    except:
        return 0.0


_RE_US_DATE  = re.compile(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})")
_RE_ISO_DATE = re.compile(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})")


def _normalize_date_val(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    v = str(val).strip()
    if not v or v in ("-", "None", "null", "nan"):
        return ""

    m2 = _RE_ISO_DATE.match(v)
    if m2:
        y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    m = _RE_US_DATE.match(v)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if p1 > 12:
            d, m = p1, p2
        elif p2 > 12:
            d, m = p2, p1
        else:
            d, m = p1, p2  # Standard DD/MM/YYYY
        return f"{y:04d}-{m:02d}-{d:02d}"

    return v[:10]


class OperationsReportModule:
    """
    مركز تقارير العمليات:
    ربط المحفظة بالسدادات برقم المديونية وحساب التغطية والتحصيل والمستهدفات.
    """

    @staticmethod
    def get_filter_options(portfolio: pl.DataFrame) -> Dict[str, List[str]]:
        if portfolio is None or len(portfolio) == 0:
            return {}
        sup_col = _detect(portfolio, _SUPERVISOR_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)

        sups = []
        if sup_col and sup_col in portfolio.columns:
            sups = sorted([str(x).strip() for x in portfolio[sup_col].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])

        cols = []
        if col_col and col_col in portfolio.columns:
            cols = sorted([str(x).strip() for x in portfolio[col_col].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])

        return {"supervisors": sups, "collectors": cols}

    def run(
        self,
        portfolio: pl.DataFrame,
        payments: Optional[pl.DataFrame] = None,
        report_mode: str = "daily",
        target_date: Optional[Any] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        supervisors: Optional[List[str]] = None,
        coverage_target: float = 200.0,
        collection_target: float = 50000.0,
        supervisor_targets: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:

        if portfolio is None or len(portfolio) == 0:
            raise ValueError("لم يتم رفع ملف المحفظة أو الملف فارغ!")

        # 1. كشف الأعمدة الحيوية في المحفظة
        debt_col_port = _detect(portfolio, _DEBT_COLS)
        sup_col       = _detect(portfolio, _SUPERVISOR_COLS)
        col_col       = _detect(portfolio, _COLLECTOR_COLS)
        followup_col  = _detect(portfolio, _FOLLOWUP_DATE_COLS)

        if not col_col:
            raise ValueError("لم يتم العثور على عمود المحصل في ملف المحفظة!")
        if not debt_col_port:
            debt_col_port = _detect(portfolio, _ID_COLS) or portfolio.columns[0]

        df_p = portfolio.clone()

        # 2. فلتر المشرفين (إن وُجد)
        if supervisors and sup_col and sup_col in df_p.columns:
            df_p = df_p.filter(pl.col(sup_col).cast(pl.String).str.strip_chars().is_in(supervisors))

        if len(df_p) == 0:
            raise ValueError("لا توجد بيانات مطابقة للمشرفين المحددين!")

        # 3. توحيد وتحديد نطاق التغطية الزمني بناءً على [تاريخ المتابعة]
        today_obj = date.today()
        report_mode = (report_mode or "daily").lower().strip()

        if followup_col and followup_col in df_p.columns:
            raw_dates = df_p[followup_col].to_list()
            norm_dates = [_normalize_date_val(d) for d in raw_dates]
            followup_series = pl.Series(norm_dates)
        else:
            followup_series = pl.Series([today_obj.strftime("%Y-%m-%d")] * len(df_p))

        if report_mode == "daily":
            target_date_str = _normalize_date_val(target_date) if target_date else today_obj.strftime("%Y-%m-%d")
            report_title = "📅 التقرير اليومي (Daily Report)"
            report_period_str = f"تاريخ التقرير: {target_date_str}"
            is_covered_expr = (followup_series == target_date_str)

        elif report_mode == "weekly":
            s_dt = _normalize_date_val(start_date) if start_date else (today_obj - timedelta(days=6)).strftime("%Y-%m-%d")
            e_dt = _normalize_date_val(end_date) if end_date else today_obj.strftime("%Y-%m-%d")
            report_title = "🗓 التقرير الأسبوعي (Weekly Report)"
            report_period_str = f"الفترة: من {s_dt} إلى {e_dt}"
            is_covered_expr = (followup_series >= s_dt) & (followup_series <= e_dt)

        elif report_mode == "monthly":
            m_val = int(month) if month else today_obj.month
            y_val = int(year) if year else today_obj.year
            month_prefix = f"{y_val:04d}-{m_val:02d}"
            report_title = "📆 التقرير الشهري (Monthly Report)"
            report_period_str = f"فترة الشهر: {month_prefix} ({m_val}/{y_val})"
            is_covered_expr = followup_series.str.starts_with(month_prefix)
        else:
            report_title = "📊 تقرير العمليات"
            report_period_str = f"التاريخ: {today_obj.strftime('%Y-%m-%d')}"
            is_covered_expr = pl.Series([True] * len(df_p))

        df_p = df_p.with_columns([
            is_covered_expr.cast(pl.Int32).alias("_is_covered"),
            pl.col(debt_col_port).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_clean_debt_id")
        ])

        # 4. معالجة شيت السدادات / التحصيل والربط بـ [رقم المديونية]
        debt_pmt_map: Dict[str, float] = {}

        if payments is not None and len(payments) > 0:
            pmt_debt_col = _detect(payments, _DEBT_COLS) or _detect(payments, _ID_COLS)
            pmt_amt_col  = _detect(payments, _PAYMENT_AMOUNT_COLS)
            pmt_dt_col   = _detect(payments, _PAYMENT_DATE_COLS)

            if pmt_debt_col and pmt_amt_col:
                pmt_clean = payments.with_columns([
                    pl.col(pmt_debt_col).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_pmt_debt_clean"),
                    pl.col(pmt_amt_col).cast(pl.String).str.replace_all(",", "", literal=True).str.replace_all(r"[^\d\.-]", "", literal=False).cast(pl.Float64, strict=False).fill_null(0.0).alias("_pmt_amt_clean")
                ])

                # تصفية السدادات بتاريخ العملية إذا وُجد عمود تاريخ وكان متوفراً
                if pmt_dt_col and pmt_dt_col in pmt_clean.columns:
                    raw_p_dates = pmt_clean[pmt_dt_col].to_list()
                    norm_p_dates = [_normalize_date_val(d) for d in raw_p_dates]
                    pmt_clean = pmt_clean.with_columns(pl.Series("_pmt_date_norm", norm_p_dates))

                    if report_mode == "daily" and 'target_date_str' in locals():
                        pmt_clean = pmt_clean.filter(pl.col("_pmt_date_norm") == target_date_str)
                    elif report_mode == "weekly" and 's_dt' in locals() and 'e_dt' in locals():
                        pmt_clean = pmt_clean.filter((pl.col("_pmt_date_norm") >= s_dt) & (pl.col("_pmt_date_norm") <= e_dt))
                    elif report_mode == "monthly" and 'month_prefix' in locals():
                        pmt_clean = pmt_clean.filter(pl.col("_pmt_date_norm").str.starts_with(month_prefix))

                # تجميع مبالغ السداد لكل مديونية
                agg_pmt = pmt_clean.group_by("_pmt_debt_clean").agg(pl.col("_pmt_amt_clean").sum().alias("_total_debt_pmt"))
                for r in agg_pmt.iter_rows(named=True):
                    d_id = str(r["_pmt_debt_clean"]).strip()
                    if d_id:
                        debt_pmt_map[d_id] = float(r["_total_debt_pmt"])

        # ربط مبلغ السداد بالمحفظة عن طريق رقم المديونية
        debt_ids_list = df_p["_clean_debt_id"].to_list()
        mapped_pmts = [debt_pmt_map.get(did, 0.0) for did in debt_ids_list]
        df_p = df_p.with_columns(pl.Series("_row_paid_amount", mapped_pmts))

        # 5. التجميع لبناء التقرير التنفيذي المطلوب بالضبط
        # الأعمدة: المشرف | المحصل | التغطية | مستهدف التغطية | نسبة التغطية % | التحصيل | مستهدف التحصيل | نسبة التحصيل %
        grp_cols = [sup_col, col_col] if sup_col and sup_col in df_p.columns else [col_col]

        agg_summary = (
            df_p.group_by(grp_cols)
            .agg([
                pl.col("_is_covered").sum().alias("التغطية"),
                pl.col("_row_paid_amount").sum().round(2).alias("التحصيل"),
                pl.len().alias("إجمالي مديونيات المحصل")
            ])
            .sort(sup_col if sup_col and sup_col in df_p.columns else col_col)
        )

        rows: List[Dict[str, Any]] = []
        supervisor_targets = supervisor_targets or {}

        def_cov_tgt = float(coverage_target if coverage_target and coverage_target > 0 else 200.0)
        def_col_tgt = float(collection_target if collection_target and collection_target > 0 else 50000.0)

        # إذا وُجد عمود مشرف نقسم حسب المشرفين مع إجماليات فرعية
        if sup_col and sup_col in agg_summary.columns:
            sup_groups: Dict[str, List[Dict[str, Any]]] = {}
            for r in agg_summary.iter_rows(named=True):
                s_name = str(r.get(sup_col) or "بدون مشرف").strip()
                sup_groups.setdefault(s_name, []).append(r)

            for s_name, cols_list in sup_groups.items():
                s_custom = supervisor_targets.get(s_name, {}) if supervisor_targets else {}
                cov_tgt_val = float(s_custom.get("coverage_target") or def_cov_tgt)
                col_tgt_val = float(s_custom.get("collection_target") or def_col_tgt)

                sup_tot_cov = 0.0
                sup_tot_col = 0.0
                sup_tot_cov_tgt = 0.0
                sup_tot_col_tgt = 0.0

                # صفوف المحصلين التابعين للمشرف
                for c_item in cols_list:
                    c_name = str(c_item.get(col_col) or "").strip()
                    c_cov  = float(c_item.get("التغطية") or 0.0)
                    c_col  = float(c_item.get("التحصيل") or 0.0)

                    c_cov_pct = round((c_cov / cov_tgt_val * 100.0), 2) if cov_tgt_val > 0 else 0.0
                    c_col_pct = round((c_col / col_tgt_val * 100.0), 2) if col_tgt_val > 0 else 0.0

                    sup_tot_cov     += c_cov
                    sup_tot_col     += c_col
                    sup_tot_cov_tgt += cov_tgt_val
                    sup_tot_col_tgt += col_tgt_val

                    rows.append({
                        "المشرف": s_name,
                        "المحصل": c_name,
                        "التغطية": int(c_cov),
                        "مستهدف التغطية": int(cov_tgt_val),
                        "نسبة التغطية %": c_cov_pct,
                        "التحصيل": round(c_col, 2),
                        "مستهدف التحصيل": round(col_tgt_val, 2),
                        "نسبة التحصيل %": c_col_pct,
                        "_row_type": "collector"
                    })

                # صف إجمالي المشرف الفرعي
                sup_cov_pct = round((sup_tot_cov / sup_tot_cov_tgt * 100.0), 2) if sup_tot_cov_tgt > 0 else 0.0
                sup_col_pct = round((sup_tot_col / sup_tot_col_tgt * 100.0), 2) if sup_tot_col_tgt > 0 else 0.0

                rows.append({
                    "المشرف": f"إجمالي مشرف: {s_name}",
                    "المحصل": f"({len(cols_list)} محصلين)",
                    "التغطية": int(sup_tot_cov),
                    "مستهدف التغطية": int(sup_tot_cov_tgt),
                    "نسبة التغطية %": sup_cov_pct,
                    "التحصيل": round(sup_tot_col, 2),
                    "مستهدف التحصيل": round(sup_tot_col_tgt, 2),
                    "نسبة التحصيل %": sup_col_pct,
                    "_row_type": "subtotal"
                })

        else:
            # بدون عمود مشرف
            for c_item in agg_summary.iter_rows(named=True):
                c_name = str(c_item.get(col_col) or "").strip()
                c_cov  = float(c_item.get("التغطية") or 0.0)
                c_col  = float(c_item.get("التحصيل") or 0.0)

                c_cov_pct = round((c_cov / def_cov_tgt * 100.0), 2) if def_cov_tgt > 0 else 0.0
                c_col_pct = round((c_col / def_col_tgt * 100.0), 2) if def_col_tgt > 0 else 0.0

                rows.append({
                    "المشرف": "-",
                    "المحصل": c_name,
                    "التغطية": int(c_cov),
                    "مستهدف التغطية": int(def_cov_tgt),
                    "نسبة التغطية %": c_cov_pct,
                    "التحصيل": round(c_col, 2),
                    "مستهدف التحصيل": round(def_col_tgt, 2),
                    "نسبة التحصيل %": c_col_pct,
                    "_row_type": "collector"
                })

        # ── صف الإجمالي العام النهائي ──
        grand_cov     = sum(r["التغطية"] for r in rows if r["_row_type"] == "collector")
        grand_cov_tgt = sum(r["مستهدف التغطية"] for r in rows if r["_row_type"] == "collector")
        grand_col     = sum(r["التحصيل"] for r in rows if r["_row_type"] == "collector")
        grand_col_tgt = sum(r["مستهدف التحصيل"] for r in rows if r["_row_type"] == "collector")

        grand_cov_pct = round((grand_cov / grand_cov_tgt * 100.0), 2) if grand_cov_tgt > 0 else 0.0
        grand_col_pct = round((grand_col / grand_col_tgt * 100.0), 2) if grand_col_tgt > 0 else 0.0

        rows.append({
            "المشرف": "🌟 الإجمالي العام للمحفظة",
            "المحصل": "الكل",
            "التغطية": int(grand_cov),
            "مستهدف التغطية": int(grand_cov_tgt),
            "نسبة التغطية %": grand_cov_pct,
            "التحصيل": round(grand_col, 2),
            "مستهدف التحصيل": round(grand_col_tgt, 2),
            "نسبة التحصيل %": grand_col_pct,
            "_row_type": "grand_total"
        })

        df_report = pl.DataFrame(rows)

        stats = {
            "نوع التقرير": report_title,
            "الفترة الزمنية": report_period_str,
            "إجمالي التغطية الفعلية": f"{int(grand_cov):,} عميل",
            "مستهدف التغطية الكلي": f"{int(grand_cov_tgt):,} عميل",
            "نسبة التغطية الكلية": f"{grand_cov_pct}%",
            "إجمالي التحصيل الفعلي": f"{grand_col:,.2f} ﷼",
            "مستهدف التحصيل الكلي": f"{grand_col_tgt:,.2f} ﷼",
            "نسبة التحصيل الكلية": f"{grand_col_pct}%",
        }

        return {
            "report_mode": report_mode,
            "report_title": report_title,
            "report_period": report_period_str,
            "report_table": df_report,
            "data": df_p,
            "stats": stats,
            "pivot_supervisor": df_report.filter(pl.col("_row_type") != "collector"),
            "pivot_collector": df_report.filter(pl.col("_row_type") == "collector"),
        }
