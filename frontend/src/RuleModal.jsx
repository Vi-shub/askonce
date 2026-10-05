export default function RuleModal({ r }) {
  const { modal, setModal, optionId, setOptionId, reason, setReason, confirm, busy } =
    r;
  if (!modal) return null;
  return (
    <div className="modal-back" onClick={() => setModal(null)}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="kicker" style={{ color: "#c45c26" }}>
          Missing rule
          {modal.proposal.used_gemini ? " · Gemini" : ""}
        </div>
        <h2>
          {modal.proposal.unexplained
            ? "That broke none of my rules."
            : "Already explained"}
        </h2>
        <p>{modal.proposal.question}</p>
        <p style={{ fontSize: 13 }}>{modal.proposal.why_unexplained}</p>
        {modal.proposal.unexplained && (
          <>
            <div className="options">
              {(modal.proposal.options || []).map((o) => (
                <button
                  key={o.id}
                  className={optionId === o.id ? "on" : ""}
                  onClick={() => setOptionId(o.id)}
                >
                  {o.label}
                </button>
              ))}
            </div>
            <textarea
              placeholder="Why? (family dinner every Saturday…)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button className="primary" onClick={confirm} disabled={busy}>
              Teach Askonce and re-solve
            </button>
          </>
        )}
      </div>
    </div>
  );
}
