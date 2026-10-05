import { useEffect, useMemo, useState } from "react";
import { api, cellOf } from "./api.js";

export function useAskonce() {
  const [ward, setWard] = useState(null);
  const [roster, setRoster] = useState(null);
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState(null);
  const [optionId, setOptionId] = useState("permanent_weekday");
  const [reason, setReason] = useState("");
  const [toast, setToast] = useState("");
  const [infeasible, setInfeasible] = useState(null);
  const [picked, setPicked] = useState(null);
  const [calloutPulse, setCalloutPulse] = useState(0);
  const [voice, setVoice] = useState(
    "Priya can't do Saturday nights — family dinner every week."
  );

  async function refresh() {
    const data = await api("/api/ward");
    setWard(data);
    setRoster(data.roster);
    setRules(data.rules || []);
    setHistory(data.history || []);
  }

  useEffect(() => {
    refresh().catch((e) => setToast(e.message || "API not running"));
  }, []);

  const maxBar = Math.max(1, ...history.map((h) => h.overrides || 0));

  async function generate() {
    setBusy(true);
    setInfeasible(null);
    setToast("");
    try {
      const res = await api("/api/generate", { method: "POST" });
      if (!res.ok) {
        setInfeasible(res.infeasible);
        return;
      }
      setRoster(res.roster);
      setToast(`Roster solved in ${res.roster.stats?.wall_time_s ?? "?"}s.`);
    } finally {
      setBusy(false);
    }
  }

  async function takeOff(nurse, day, fromShift) {
    if (!fromShift || fromShift === "off") return;
    setBusy(true);
    try {
      const ov = {
        nurse_id: nurse.id,
        day_index: day,
        from_shift: fromShift,
        to_shift: "off",
        manager: "Nurse Manager Sato",
      };
      const proposal = await api("/api/override/propose", {
        method: "POST",
        body: JSON.stringify(ov),
      });
      setModal({ ov, proposal, nurse });
      setOptionId("permanent_weekday");
      setReason("");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!modal) return;
    setBusy(true);
    try {
      const res = await api("/api/override/confirm", {
        method: "POST",
        body: JSON.stringify({
          override: modal.ov,
          option_id: optionId,
          free_text: reason,
          manager: "Nurse Manager Sato",
        }),
      });
      if (!res.ok) {
        setInfeasible(res.infeasible);
        setModal(null);
        return;
      }
      setRoster(res.roster);
      setRules(res.rules);
      setHistory(res.history);
      setToast(`Learned: ${res.rule.reason} — taught by ${res.rule.taught_by}.`);
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  const priyaSaturdayNight = useMemo(() => {
    if (!roster || !ward) return null;
    const priya = ward.nurses.find((n) => n.id === "n04");
    const sat = ward.days.find((d) => d.weekday === 5);
    if (!priya || !sat) return null;
    const shift = cellOf(roster, "n04", sat.index);
    return { nurse: priya, day: sat.index, shift };
  }, [roster, ward]);

  async function demoPriya() {
    if (!priyaSaturdayNight || priyaSaturdayNight.shift === "off") {
      setToast("Generate a roster first, then run the Priya demo.");
      return;
    }
    await takeOff(
      priyaSaturdayNight.nurse,
      priyaSaturdayNight.day,
      priyaSaturdayNight.shift
    );
  }

  async function demoCallout() {
    if (!roster) return;
    const night =
      roster.assignments.find((a) => a.shift === "night" && a.nurse_id === "n06") ||
      roster.assignments.find((a) => a.shift === "night");
    if (!night) return;
    setBusy(true);
    try {
      const res = await api("/api/callout", {
        method: "POST",
        body: JSON.stringify({
          nurse_id: night.nurse_id,
          day_index: night.day_index,
          shift: "night",
          reason: "called in sick at 23:10",
        }),
      });
      if (!res.ok) {
        setInfeasible(res.infeasible);
        return;
      }
      setRoster(res.roster);
      setPicked(res.picked);
      setCalloutPulse((n) => n + 1);
      setToast(`Callout covered. Asked ${res.picked.name}.`);
    } finally {
      setBusy(false);
    }
  }

  async function illegalYamadaNight() {
    setBusy(true);
    setInfeasible(null);
    try {
      const res = await api("/api/force", {
        method: "POST",
        body: JSON.stringify({
          nurse_id: "n03",
          day_index: 0,
          shift: "night",
        }),
      });
      if (!res.ok) {
        setInfeasible(res.infeasible);
        setToast("Askonce refused. That is the point.");
        return;
      }
      setRoster(res.roster);
    } finally {
      setBusy(false);
    }
  }

  async function sendVoice() {
    setBusy(true);
    try {
      const res = await api("/api/voice-rule", {
        method: "POST",
        body: JSON.stringify({ text: voice }),
      });
      if (!res.ok) {
        setToast(res.error || "Could not parse");
        return;
      }
      const nurse = ward.nurses.find((n) => n.id === res.override.nurse_id);
      setModal({ ov: res.override, proposal: res.proposal, nurse });
    } finally {
      setBusy(false);
    }
  }

  return {
    ward,
    roster,
    rules,
    history,
    busy,
    modal,
    setModal,
    optionId,
    setOptionId,
    reason,
    setReason,
    toast,
    infeasible,
    picked,
    calloutPulse,
    voice,
    setVoice,
    maxBar,
    generate,
    takeOff,
    confirm,
    demoPriya,
    demoCallout,
    illegalYamadaNight,
    sendVoice,
    priyaSaturdayNight,
  };
}
