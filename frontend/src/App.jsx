import { useEffect, useState } from "react";
import Desk from "./Desk.jsx";
import Phone from "./Phone.jsx";
import RuleModal from "./RuleModal.jsx";
import { useAskonce } from "./useAskonce.js";

function initialLayout() {
  const hash = window.location.hash.replace("#", "");
  if (hash === "phone") return "phone";
  if (hash === "split") return "split";
  if (window.matchMedia("(display-mode: standalone)").matches) return "phone";
  if (window.innerWidth < 820) return "phone";
  return "desk";
}

export default function App() {
  const r = useAskonce();
  const [layout, setLayout] = useState(initialLayout);

  useEffect(() => {
    window.location.hash = layout === "desk" ? "" : layout;
  }, [layout]);

  if (!r.ward) {
    return (
      <div className="main">
        <p>Waiting for API on :8000…</p>
      </div>
    );
  }

  return (
    <div className={`shell layout-${layout}`}>
      <div className="shell-bar">
        <span className="kicker">Askonce</span>
        <div className="shell-switch">
          <button
            className={layout === "desk" ? "on" : ""}
            onClick={() => setLayout("desk")}
          >
            Desk
          </button>
          <button
            className={layout === "phone" ? "on" : ""}
            onClick={() => setLayout("phone")}
          >
            Phone
          </button>
          <button
            className={layout === "split" ? "on" : ""}
            onClick={() => setLayout("split")}
          >
            Side by side
          </button>
        </div>
        <span className="mono shell-hint">
          Desk writes the roster. Phone covers 23:10.
        </span>
      </div>
      <div className="shell-body">
        {layout !== "phone" && (
          <div className="shell-desk">
            <Desk r={r} />
          </div>
        )}
        {layout !== "desk" && (
          <div className="shell-phone">
            <Phone r={r} />
          </div>
        )}
      </div>
      <RuleModal r={r} />
    </div>
  );
}
