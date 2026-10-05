import { useEffect, useState } from "react";

export default function Phone({ r, framed = true }) {
  const {
    ward,
    roster,
    rules,
    busy,
    picked,
    calloutPulse,
    voice,
    setVoice,
    startDemo,
    demoPriya,
    demoCallout,
    sendVoice,
    infeasible,
  } = r;
  const [tab, setTab] = useState("nurse");
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    if (calloutPulse > 0) {
      setTab("nurse");
      setAccepted(false);
    }
  }, [calloutPulse]);

  const inner = (
    <div className={`phone-ui ${calloutPulse ? "pulse" : ""}`}>
      <div className="phone-status">
        <span>23:10</span>
        <span>Askonce</span>
        <span>5G</span>
      </div>
      <div className="phone-tabs">
        <button className={tab === "nurse" ? "on" : ""} onClick={() => setTab("nurse")}>
          Nurse
        </button>
        <button
          className={tab === "manager" ? "on" : ""}
          onClick={() => setTab("manager")}
        >
          Manager
        </button>
      </div>

      {tab === "nurse" && (
        <div className="phone-body">
          <p className="kicker">Incoming cover request</p>
          {!picked && (
            <div className="sms muted-card">
              No ping yet. On the desk, hit <b>23:10 callout</b> — this phone is
              who gets asked, not the same three people every time.
            </div>
          )}
          {picked && (
            <>
              <div className={`sms ${accepted ? "ok" : "live"}`}>
                <div className="kicker">{picked.legal ? "Fairness pick" : "Blocked"}</div>
                <h2 className="serif" style={{ margin: "6px 0 8px", fontSize: 28 }}>
                  {picked.name}
                </h2>
                <p>{picked.why}</p>
                <p className="mono sms-bubble">{picked.message}</p>
              </div>
              <div className="phone-actions">
                <button
                  className="primary"
                  disabled={!picked.legal || accepted}
                  onClick={() => setAccepted(true)}
                >
                  {accepted ? "You're covering" : "I can cover"}
                </button>
                <button className="ghost" onClick={() => setAccepted(false)}>
                  Can't tonight
                </button>
              </div>
            </>
          )}
          <p className="phone-foot">
            Hands are dirty. This is a 12-second yes/no — not a roster grid.
          </p>
        </div>
      )}

      {tab === "manager" && (
        <div className="phone-body">
          <p className="kicker">Manager · on the floor</p>
          <h2 className="serif" style={{ marginTop: 0, fontSize: 26 }}>
            Teach a rule from here
          </h2>
          <p style={{ color: "#cfc3ab", fontSize: 14 }}>
            {roster
              ? `${ward.nurses.length} on the book · ${rules.length} taught rules`
              : "No roster yet."}
          </p>
          <div className="phone-actions">
            <button className="primary" disabled={busy} onClick={startDemo}>
              {roster ? "Reset demo" : "Start demo"}
            </button>
            <button className="ghost" disabled={busy || !roster} onClick={demoCallout}>
              Send 23:10 ping
            </button>
            <button className="ghost" disabled={busy || !roster} onClick={demoPriya}>
              Priya off Saturday
            </button>
          </div>
          <textarea
            className="phone-voice"
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
          />
          <button className="primary" disabled={busy} onClick={sendVoice}>
            Parse into a rule
          </button>
          {infeasible && (
            <div className="infeasible" style={{ marginTop: 12 }}>
              {infeasible.summary}
            </div>
          )}
          <div className="phone-rules">
            {rules.map((rule) => (
              <div className="rule" key={rule.id}>
                {rule.reason}
                <div className="who mono">{rule.taught_by}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  if (!framed) return inner;
  return (
    <div className="phone-frame">
      <div className="phone-notch" />
      {inner}
    </div>
  );
}
