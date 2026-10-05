import { cellOf, cellTaught } from "./api.js";

export default function Desk({ r }) {
  const {
    ward,
    roster,
    rules,
    history,
    busy,
    toast,
    infeasible,
    picked,
    voice,
    setVoice,
    maxBar,
    generate,
    takeOff,
    demoPriya,
    demoCallout,
    illegalYamadaNight,
    sendVoice,
    startDemo,
    gemini,
  } = r;

  return (
    <div className="app">
      <aside className="rail">
        <div className="kicker">Desk · Ward 4 East</div>
        <h1 className="pitch">{ward.pitch}</h1>
        <p className="mono" style={{ color: "#cfc3ab", fontSize: 12 }}>
          {ward.ward.hospital} · {ward.num_days}-day horizon
          {gemini ? " · Gemini on" : " · heuristic (add GEMINI_API_KEY)"}
        </p>
        <ul className="policy">
          {ward.ward.policy.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <div className="kicker" style={{ marginTop: 28 }}>
          Overrides falling
        </div>
        <div className="chart">
          {history.map((h) => (
            <div
              key={h.cycle}
              className="bar"
              title={`${h.cycle}: ${h.overrides} overrides, ${h.rules_known} rules`}
              style={{ height: `${(h.overrides / maxBar) * 88}px` }}
            />
          ))}
        </div>
        <p className="mono" style={{ fontSize: 11, color: "#8a8274" }}>
          Configuration drift dying in public.
        </p>
      </aside>

      <main className="main">
        <div className="toolbar">
          <button className="primary" disabled={busy} onClick={startDemo}>
            Start demo
          </button>
          <button className="ghost" disabled={busy} onClick={generate}>
            Re-solve
          </button>
          <button className="ghost" disabled={busy || !roster} onClick={demoPriya}>
            Demo: Priya off Saturday
          </button>
          <button className="ghost" disabled={busy || !roster} onClick={demoCallout}>
            23:10 callout
          </button>
          <button className="danger" disabled={busy} onClick={illegalYamadaNight}>
            Force Yamada onto nights
          </button>
          <span className="mono" style={{ fontSize: 12, color: "#8a8274" }}>
            Click a shift to take it off. That is the training signal.
          </span>
        </div>

        {infeasible && (
          <div className="infeasible">
            <strong>Refused — legally.</strong>
            <p>{infeasible.summary}</p>
            <ul>
              {(infeasible.legal_choices || []).map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid-wrap">
          <table className="roster">
            <thead>
              <tr>
                <th>Nurse</th>
                {ward.days.map((d) => (
                  <th key={d.index} className={d.weekend ? "weekend" : ""}>
                    {d.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ward.nurses.map((n) => (
                <tr key={n.id}>
                  <td className="name">
                    {n.name}
                    <small>
                      {n.role}
                      {n.legal_flags?.length ? " · legal flag" : ""}
                      {` · callouts ${n.prior_callouts}`}
                    </small>
                  </td>
                  {ward.days.map((d) => {
                    const shift = cellOf(roster, n.id, d.index) || "off";
                    const taught = cellTaught(rules, n.id, d.index, d.weekday);
                    return (
                      <td key={d.index}>
                        <div
                          className={`cell ${shift}${taught ? " taught" : ""}`}
                          onClick={() => takeOff(n, d.index, shift)}
                          title={taught ? "Taught rule" : "Take off this shift"}
                        >
                          {shift === "off" ? "—" : shift}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {toast && <div className="toast">{toast}</div>}
        {picked && (
          <div className="toast">
            <div className="kicker">Ask this person</div>
            <p>
              <strong>{picked.name}</strong> — {picked.why}
            </p>
            <p className="mono">{picked.message}</p>
          </div>
        )}
      </main>

      <aside className="side">
        <div className="kicker">Rule memory</div>
        <h2 className="serif" style={{ marginTop: 6 }}>
          {rules.length} taught rules
        </h2>
        {rules.length === 0 && (
          <p style={{ color: "#8a8274", fontSize: 14 }}>
            Empty on purpose. The first drag writes the first unwritten rule.
          </p>
        )}
        {rules.map((rule) => (
          <div className="rule" key={rule.id}>
            <div>{rule.reason}</div>
            <div className="who mono">
              {rule.taught_by} · {rule.scope}
              {rule.taught_at ? ` · ${rule.taught_at.slice(0, 16).replace("T", " ")}` : ""}
            </div>
            {rule.source_override && (
              <div className="who mono">from {rule.source_override}</div>
            )}
          </div>
        ))}

        <div className="kicker" style={{ marginTop: 28 }}>
          Voice → rule
        </div>
        <div className="voice">
          <input value={voice} onChange={(e) => setVoice(e.target.value)} />
          <button className="ghost" onClick={sendVoice} disabled={busy}>
            Parse
          </button>
        </div>
      </aside>
    </div>
  );
}
