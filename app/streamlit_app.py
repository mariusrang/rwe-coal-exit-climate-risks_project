"""RWE coal exit dashboard (Climate Risks, IDSI 51003).

Run from the repo root:   streamlit run app/streamlit_app.py
Needs the files in results/ (created by the last cell of notebooks/RWE_coal_exit_final_project.ipynb).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

st.set_page_config(page_title="RWE coal exit tracker", page_icon="⚡", layout="wide")

COL = {"Track record": "#eb6834", "Current plan": "#2a78d6", "Full delivery": "#1baf7a",
       "coal": "#52514e", "gas": "#eb6834", "offshore": "#1c5cab", "onshore": "#2a78d6", "solar": "#eda100",
       "red": "#e34948", "muted": "#9a9893"}


@st.cache_data
def load():
    P = json.loads((RES / "params.json").read_text())
    names = ["rwe_pipeline_units", "rwe_coal_units", "rwe_history", "scenario_summary", "sensitivities",
             "europe_country_gap", "peers_europe", "europe_coal_plants_exposure", "intensity_gap", "emission_paths",
             "emissions_calibration", "carbon_cost_ratio", "offshore_evidence", "criterion_c2", "iea_benchmark"]
    return P, {n: pd.read_csv(RES / f"{n}.csv") for n in names}


P, D = load()
pipe, coal, hist = D["rwe_pipeline_units"], D["rwe_coal_units"], D["rwe_history"]
H = P["H_YEAR"]


@st.cache_data
def simulate(ontime, vanguard, ncb, undated, adjusted, perimeter, timing, rho_off, full, n=4000, seed=42):
    rng = np.random.default_rng(seed)
    gw = pipe.gw.to_numpy()
    tech = pipe.tech.to_numpy()
    p = np.where(pipe.is_off_ev, pipe.p_main,
                 np.where(pipe.is_con, P["p_con"],
                          (pipe.p_main + (pipe.p_undated if undated else 0)) * ontime / P["on_time"])).astype(float)
    p = np.where(pipe.name.str.startswith("Norfolk Vanguard"), vanguard, p)
    p = np.where(pipe.name.isin(["Nordsee 3 wind farm", "Delta Nordsee wind farm"]), ncb, p)
    if full:
        p = (pipe.p_full + 0.8 * (pipe.p_undated > 0)).to_numpy(float)
    p = np.clip(p, 0, 1)
    mask = np.ones(len(gw))
    if perimeter == "Germany + Netherlands":
        mask *= pipe.de_nl.to_numpy()
    if timing == "Online before 31 Mar 2030":
        mask *= pipe.in_exit.to_numpy()
    a = np.where((tech != "offshore") & adjusted, 1 / P["coverage"], 1.0)
    is_off = tech == "offshore"
    z_off, z_rest, e = rng.standard_normal(n), rng.standard_normal(n), rng.standard_normal((n, len(gw)))
    lat = np.where(is_off, np.sqrt(rho_off) * z_off[:, None] + np.sqrt(1 - rho_off) * e,
                   np.sqrt(0.3) * z_rest[:, None] + np.sqrt(0.7) * e)
    on = (stats.norm.cdf(lat) < p).astype(float) * mask
    cf = {k: rng.triangular(*v, n) for k, v in P["cf_range"].items()}
    unit_cf = np.column_stack([cf[t] for t in tech])
    return on @ (gw * a), (on * unit_cf) @ (gw * a) * H, cf["coal"]


# ------------------------------------------------------------------ header
st.title("⚡ Is RWE on track for its 2030 coal exit?")
st.caption("Climate Risks (IDSI 51003) · Victor Henz, Edgar Gusching, Marius Rang, Ylias Guetari · "
           f"Data: {P['source']}")

sc = D["scenario_summary"].set_index(["scenario", "basis"])
cp = sc.loc[("Current plan", "GEM")]
k = st.columns(5)
k[0].metric("Replacement ratio 2030 (Current plan)", f"{cp.ratio_median:.2f}",
            f"90%: {cp.ratio_p05:.2f}–{cp.ratio_p95:.2f}", delta_color="off")
k[1].metric("Germany + Netherlands only", f"{P['metric']['GEM-visible']['Germany + Netherlands only']:.2f}")
k[2].metric("Pace needed (end 2030)", f"{P['req_pace']['end of 2030 (5 years)']:.2f} GW/yr")
k[3].metric("Pace of named, dated projects", f"{cp.implied_pace_GW_yr:.2f} GW/yr")
k[4].metric("RWE guidance 2026-31 (incl. batteries)", f"{P['guidance_pace']:.2f} GW/yr")

tabs = st.tabs(["🎛️ Simulator", "🌍 Sector view", "🏭 RWE coal fleet", "🌊 Pipeline evidence", "📉 Emissions & carbon cost", "📚 Method"])

# ------------------------------------------------------------------ simulator
with tabs[0]:
    st.subheader("Does RWE's new wind + solar replace the output of its coal?")
    left, right = st.columns([1, 2.2])
    with left:
        preset = st.radio("Scenario", ["Current plan", "Full delivery"], horizontal=True)
        full = preset == "Full delivery"
        st.markdown("**Pipeline**")
        ontime = st.slider("Slippage factor (share of dated projects on time)", 0.4, 1.0, float(P["on_time"]), 0.05, disabled=full)
        vanguard = st.slider("Norfolk Vanguard: probability online by 2030", 0.0, 1.0, 0.60, 0.05, disabled=full)
        ncb = st.slider("Nordseecluster B: probability online by 2030", 0.0, 1.0, 0.85, 0.05, disabled=full)
        undated = st.checkbox("Include undated onshore / solar projects", False, disabled=full)
        rho = st.slider("Correlation between offshore projects (ρ)", 0.0, 0.9, 0.5, 0.1)
        st.markdown("**Scope and timing**")
        perimeter = st.radio("Perimeter", ["Portfolio (worldwide)", "Germany + Netherlands"], horizontal=True)
        timing = st.radio("Count capacity", ["Online by end 2030", "Online before 31 Mar 2030"], horizontal=True)
        adjusted = st.checkbox(f"Coverage-adjusted basis (onshore/solar ÷ {P['coverage']:.2f})", False)
        st.markdown("**Coal side**")
        include_eems = st.checkbox("Count Eemshaven (GEM wrongly lists it under E.ON)", True)
        include_gkm = st.checkbox("Count GKM Mannheim (40% stake, equity consolidation)", True)
        ccf = st.slider("Effective coal capacity factor before exit", 0.30, 0.65, round(P["coal_cf_eff"], 2), 0.01,
                        help="0.50 × calibration factor B on reported CO₂")

    coal_gw = coal.coal_mw.sum() / 1000
    if not include_eems:
        coal_gw -= coal.loc[coal.corrected, "coal_mw"].sum() / 1000
    if not include_gkm:
        coal_gw -= coal.loc[coal.label.str.startswith("GKM"), "coal_mw"].sum() / 1000
    new_gw, new_twh, coal_cf_draw = simulate(ontime, vanguard, ncb, undated, adjusted, perimeter, timing, rho, full)
    coal_twh = coal_gw * coal_cf_draw / P["cf_mode"]["coal"] * ccf * H
    ratio = new_twh / coal_twh

    with right:
        m = st.columns(4)
        m[0].metric("Median ratio", f"{np.median(ratio):.2f}")
        m[1].metric("90% interval", f"{np.percentile(ratio, 5):.2f} – {np.percentile(ratio, 95):.2f}")
        pr = (ratio >= 1).mean()
        m[2].metric("P(ratio ≥ 1)", f"≈ {round(pr * 20) / 20:.2f}")
        m[3].metric("New GW by 2030", f"{np.median(new_gw):.1f}")
        fig = go.Figure()
        fig.add_histogram(x=ratio, marker_color=COL["Full delivery" if full else "Current plan"], opacity=0.75,
                          xbins=dict(start=0, end=2.5, size=0.04))
        fig.add_vline(x=1, line_dash="dash", line_color="black", line_width=2, layer="above", annotation_text="ratio = 1")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), template="simple_white",
                          xaxis_title="Replacement ratio in 2030 (new wind+solar TWh ÷ coal TWh)", yaxis_title="draws")
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"Coal output to replace: **{coal_gw:.2f} GW → {np.median(coal_twh):.1f} TWh/yr**. "
                f"Pace needed for ratio = 1 ≈ **{np.median(coal_twh) / (P['pipe_cf'] * H) / 5:.2f} GW/yr** "
                f"(RWE best 3-year average: {P['pace']['GEM-visible']['best 3-year average']:.2f} GEM-visible, "
                f"{P['pace']['coverage-adjusted']['best 3-year average']:.2f} coverage-adjusted).")
    st.markdown("**Notebook results (5,000 draws, correlated projects)**")
    st.dataframe(D["scenario_summary"].round(2), use_container_width=True, hide_index=True)
    st.markdown("**Criterion C2: pace needed vs RWE's best 3-year pace, same basis**")
    st.dataframe(D["criterion_c2"].rename(columns={"Unnamed: 0": "basis"}).round(2), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ sector
with tabs[1]:
    st.subheader("Europe's coal exit: the sector before the company")
    price = st.select_slider("Carbon price (€/tCO₂)", options=[50, 82, 100, 150], value=100)
    pl = D["europe_coal_plants_exposure"].copy()
    pl["cost"] = pl["MtCO2"] * price / 1000
    c1, c2 = st.columns([1.3, 1])
    with c1:
        fig = px.scatter_geo(pl, lat="lat", lon="lon", size="MtCO2", color=np.where(pl.is_RWE, "RWE", "other owners"),
                             hover_name="Plant / Project name",
                             hover_data={"GW": ":.2f", "MtCO2": ":.1f", "cost": ":.2f", "lat": False, "lon": False},
                             color_discrete_map={"RWE": COL["Current plan"], "other owners": COL["muted"]},
                             scope="europe", height=460, size_max=28)
        fig.update_geos(lataxis_range=[35, 62], lonaxis_range=[-10, 32], showcountries=True, countrycolor="#ccc")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        t = pl.nlargest(12, "cost")
        fig = px.bar(t, x="cost", y="Plant / Project name", orientation="h", height=460, template="simple_white",
                     color=np.where(t.is_RWE, "RWE", "other"), color_discrete_map={"RWE": COL["Current plan"], "other": COL["muted"]},
                     labels={"cost": f"Carbon cost at €{price}/t (bn €/yr)", "Plant / Project name": ""})
        fig.update_layout(showlegend=False, margin=dict(l=0, r=10, t=10, b=0), yaxis_categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Yearly carbon bill of the operating European coal fleet at €{price}/t: **€{pl.cost.sum():.1f} bn**.")
    c1, c2 = st.columns(2)
    with c1:
        ct = D["europe_country_gap"].sort_values("gap_TWh")
        fig = px.bar(ct, x="gap_TWh", y="country", orientation="h", template="simple_white", height=420,
                     color=np.where(ct.gap_TWh >= 0, "surplus", "gap"), color_discrete_map={"surplus": COL["Full delivery"], "gap": COL["Track record"]},
                     labels={"gap_TWh": "Expected new wind+solar minus coal output (TWh/yr)", "country": ""})
        fig.update_layout(title="Countries", showlegend=False, yaxis_categoryorder="array", yaxis_categoryarray=list(ct.country))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        pe = D["peers_europe"][D["peers_europe"].coal_GW >= 0.5].sort_values("gap_TWh")
        fig = go.Figure()
        fig.add_bar(y=pe.company, x=-pe.coal_TWh, orientation="h", name="coal output", marker_color=COL["coal"])
        fig.add_bar(y=pe.company, x=pe.exp_new_RE_TWh, orientation="h", name="expected new wind + solar", marker_color=COL["Current plan"])
        fig.update_layout(barmode="relative", template="simple_white", height=420, title="European utilities (European assets)",
                          xaxis_title="TWh/yr (coal to the left)", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ coal fleet
with tabs[2]:
    st.subheader("RWE's coal units and when they close")
    reserve = st.toggle("Show the reserve option (3 units kept until end 2033)", value=True)
    c = coal.sort_values(["close_contract", "coal_mw"], ascending=[True, False]).copy()
    fig = go.Figure()
    for _, r in c.iterrows():
        start = max(r["Start year"], 2015)
        fig.add_bar(y=[r.label], x=[r.close_contract - start], base=[start], orientation="h",
                    marker_color=COL["coal"] if r.kind == "lignite" else COL["muted"], showlegend=False,
                    hovertemplate=f"{r.label}<br>{r.kind}, {r.coal_mw:.0f} MW (equity, coal part)<br>closes {int(r.close_contract)}<extra></extra>")
        if reserve and r.close_reserve > r.close_contract:
            fig.add_bar(y=[r.label], x=[r.close_reserve - r.close_contract], base=[r.close_contract], orientation="h",
                        marker_color=COL["red"], opacity=0.5, showlegend=False, hovertemplate="reserve until 2033<extra></extra>")
    fig.add_vline(x=2030.25, line_color=COL["red"], annotation_text="31 Mar 2030")
    fig.update_layout(barmode="overlay", height=520, template="simple_white", xaxis_title="Year",
                      yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("Eemshaven is RWE's but GEM lists it under Essent / E.ON: we add it back (75% coal share). "
                "In August 2026 Berlin let the review deadline pass without deciding on the 2030-2033 reserve.")

# ------------------------------------------------------------------ evidence
with tabs[3]:
    st.subheader("RWE offshore wind: GEM status vs public evidence (Nov 2026)")
    st.dataframe(D["offshore_evidence"].round(2), use_container_width=True, hide_index=True)
    exp = pipe.assign(exp_gw=pipe.p_main * pipe.gw, region=np.where(pipe.de_nl, "Germany + Netherlands", "Elsewhere"))
    fig = px.bar(exp.groupby(["region", "tech"]).exp_gw.sum().reset_index(), x="exp_gw", y="region", color="tech",
                 orientation="h", template="simple_white", height=280, color_discrete_map=COL,
                 labels={"exp_gw": "Expected new GW by 2030 (main case)", "region": ""})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("**IEA benchmark (pro rata to RWE's 2022 capacity)**")
    st.dataframe(D["iea_benchmark"].round(2), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ emissions
with tabs[4]:
    st.subheader("SBTi intensity target and carbon cost")
    gap = D["intensity_gap"]
    case = st.radio("Coal case", sorted(gap["coal case"].unique()), horizontal=True)
    g = gap[gap["coal case"] == case]
    fig = go.Figure()
    fig.add_bar(x=g.scenario, y=g.intensity_t_MWh, marker_color=[COL[s] for s in g.scenario],
                error_y=dict(type="data", symmetric=False, array=g.intensity_p95 - g.intensity_t_MWh,
                             arrayminus=g.intensity_t_MWh - g.intensity_p05))
    fig.add_hline(y=P["int_target"], line_dash="dash", line_color=COL["red"], line_width=2, layer="above",
                  annotation_text=f"SBTi 2030 target {P['int_target']:.3f} t/MWh (−71.1% vs published 2022)")
    fig.update_layout(template="simple_white", height=360, yaxis_title="tCO₂ per MWh in 2030", showlegend=False)
    c1, c2 = st.columns([1.2, 1])
    c1.plotly_chart(fig, use_container_width=True)
    c2.dataframe(g[["scenario", "emissions_Mt", "generation_TWh", "intensity_t_MWh", "status"]].round(3),
                 use_container_width=True, hide_index=True)
    st.markdown("**Carbon cost / EBITDA** (a flow ratio, gross of pass-through and of the €2.6 bn exit compensation; not a VaR)")
    price = st.slider("Carbon price (€/t)", 30, 200, 82, 1)
    em25 = D["emissions_calibration"].set_index("year").loc[2025, "reported_Mt"]
    rows = [("2025 reported / EBITDA 2025", em25 * price / 1000 / P["ebitda_2025"])]
    for _, r in gap[gap.scenario == "Current plan"].iterrows():
        rows.append((f"2030 {r['coal case']} / EBITDA 2027 guidance", r.emissions_Mt * price / 1000 / P["ebitda_2027"]))
    v = pd.DataFrame(rows, columns=["case", "ratio"])
    fig = px.bar(v, x="case", y="ratio", text=v.ratio.map("{:.0%}".format), template="simple_white", height=340,
                 labels={"ratio": "Carbon cost / EBITDA", "case": ""})
    fig.update_traces(marker_color=COL["Current plan"])
    fig.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ method
with tabs[5]:
    st.markdown(f"""
**Metric.** Replacement ratio = expected output of new wind + solar online by 2030 ÷ output of the coal RWE committed to close (TWh/yr).
It is a portfolio metric; the Germany + Netherlands perimeter shows the local replacement.

**Probabilities.** Construction 0.95; dated pre-construction = GEM-wide MW-weighted build rate × {P['on_time']} (onshore {P['build_rate']['onshore']:.2f},
solar {P['build_rate']['solar']:.2f}); dated announced = half; undated = 0 (option). RWE offshore projects are set from public evidence (tab "Pipeline evidence").
Projects are correlated through a common shock per group (Gaussian copula).

**Calibration.** Coal capacity factor 0.50 × B = {P['coal_cf_eff']:.2f}, with B = {P['B']:.2f} fitted on RWE's official Scope 1 emissions (2019, 2021-2023, 2025) and drawn from its sampling distribution in the notebook's Monte Carlo.

**Two bases.** GEM sees about {P['coverage']:.0%} of RWE's wind + solar; "coverage-adjusted" divides onshore/solar (pipeline and history) by that share.
Offshore projects were checked one by one, so they are not adjusted.

**Decision criteria (set after the V0 feedback, before the final analysis).** C1: P(ratio ≥ 1) ≥ 0.66 under the Current plan. C2: pace needed ≤ best 3-year average pace, decisive basis = coverage-adjusted.

**Note.** Under our model assumptions RWE's 2030 intensity stays above its SBTi target; the calibration uses five points and constant gas utilisation.

**Use of AI tools.** We used an AI assistant (Claude, Anthropic) to help write code, draft text and build this app; choices and results were checked by the team.
""")
    st.dataframe(D["sensitivities"], use_container_width=True, hide_index=True)
