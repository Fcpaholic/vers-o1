import { useState } from 'react';

// ─── Data ────────────────────────────────────────────────────────────────────

const SUBJECTS = {
  pt: {
    1: 'Atualização sobre a tua candidatura',
    2: 'Atualização sobre a tua candidatura',
    3: 'Próximos passos – processo de seleção',
    4: 'Atualização sobre a tua candidatura',
  },
  en: {
    1: 'Update on your application',
    2: 'Update on your application',
    3: 'Next steps – selection process',
    4: 'Update on your application',
  },
};

const SCENARIO_LABELS = {
  pt: {
    1: 'Outros perfis selecionados',
    2: 'Posição preenchida',
    3: 'Avançar para próxima etapa',
    4: 'Posição cancelada',
  },
  en: {
    1: 'Other profiles were selected',
    2: 'Position was filled',
    3: 'Moving to next stage',
    4: 'Position was cancelled',
  },
};

function buildMessage(lang, scenario, name, reason) {
  const n = name.trim() || '[Candidate Name]';
  const r = reason.trim();

  if (lang === 'pt') {
    switch (scenario) {
      case 1:
        return [
          `Olá ${n},`,
          `Obrigado/a por teres dedicado o teu tempo ao nosso processo e pelo interesse nesta oportunidade.`,
          `Após ponderação cuidada, a equipa de hiring decidiu avançar com outros candidatos cujos perfis se alinham melhor com o que procuram nesta fase.${r ? `\n\nEm particular, ${r}.` : ''}`,
          `Ficou claro que tens muito para oferecer e gostaríamos de manter o teu perfil em mente para oportunidades futuras. Não hesites em entrar em contacto — será um prazer.`,
          `Com os melhores cumprimentos`,
        ].join('\n\n');

      case 2:
        return [
          `Olá ${n},`,
          `Obrigado/a pela tua paciência ao longo deste processo e pelo tempo que investiste.`,
          `Queria informar-te de que a posição foi entretanto preenchida, pelo que não podemos avançar com a tua candidatura para esta função em particular.${r ? `\n\n${r}.` : ''}`,
          `Foi um prazer conhecer-te e ficamos com o teu perfil para oportunidades futuras. Desejo-te o maior sucesso!`,
          `Com os melhores cumprimentos`,
        ].join('\n\n');

      case 3:
        return [
          `Olá ${n},`,
          `Temos boas notícias — gostaríamos de te convidar para a próxima etapa do processo!`,
          `O passo seguinte seria uma chamada por Teams com a nossa equipa. Podes partilhar a tua disponibilidade para os próximos dias para que possamos marcar um horário que funcione para ti?`,
          `Fico à tua espera e estou disponível para qualquer questão.`,
          `Com os melhores cumprimentos`,
        ].join('\n\n');

      case 4:
        return [
          `Olá ${n},`,
          `Espero que estejas bem. Queria partilhar uma atualização importante sobre a posição para a qual te candidataste.`,
          `Infelizmente, a posição foi cancelada. Esta decisão não reflete de forma alguma a tua candidatura — o teu perfil genuinamente chamou a nossa atenção.${r ? `\n\n${r}.` : ''}`,
          `Ficamos com os teus dados e entraremos em contacto assim que surgir uma oportunidade que se encaixe bem. Muito obrigado/a pelo teu tempo e interesse.`,
          `Com os melhores cumprimentos`,
        ].join('\n\n');

      default:
        return '';
    }
  } else {
    switch (scenario) {
      case 1:
        return [
          `Hi ${n},`,
          `Thank you for taking the time to go through our process and for your interest in this opportunity.`,
          `After careful consideration, the hiring team has decided to move forward with other candidates whose profiles more closely match what they're looking for at this stage.${r ? `\n\nSpecifically, ${r}.` : ''}`,
          `It's clear you have a lot to offer, and we'd love to keep your profile in mind for future opportunities. Please don't hesitate to reach out — it would be a pleasure.`,
          `Best regards`,
        ].join('\n\n');

      case 2:
        return [
          `Hi ${n},`,
          `Thank you for your patience throughout this process and for the time you invested.`,
          `I wanted to let you know that the position has been filled, so we won't be moving forward with your application for this particular role.${r ? `\n\n${r}.` : ''}`,
          `It was great getting to know you, and we'll definitely keep your profile on file for future opportunities. Wishing you all the best!`,
          `Best regards`,
        ].join('\n\n');

      case 3:
        return [
          `Hi ${n},`,
          `Great news — we'd love to move you forward to the next stage of the process!`,
          `The next step would be a Teams call with our team. Could you share your availability for the next few days so we can find a time that works for you?`,
          `Looking forward to it, and feel free to reach out if you have any questions.`,
          `Best regards`,
        ].join('\n\n');

      case 4:
        return [
          `Hi ${n},`,
          `I hope you're doing well. I wanted to share an important update regarding the role you applied for.`,
          `Unfortunately, the position has been cancelled. This decision is in no way a reflection of your candidacy — your profile genuinely stood out to us.${r ? `\n\n${r}.` : ''}`,
          `We'll keep your details on file and will be in touch as soon as a suitable opportunity comes up. Thank you so much for your time and interest.`,
          `Best regards`,
        ].join('\n\n');

      default:
        return '';
    }
  }
}

// ─── Styles (inline to keep single-file simplicity) ──────────────────────────

const S = {
  page: {
    minHeight: '100vh',
    background: '#f5f5f7',
    display: 'flex',
    justifyContent: 'center',
    padding: '40px 20px 64px',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  inner: { width: '100%', maxWidth: '640px' },
  heading: { fontSize: '22px', fontWeight: 600, color: '#1d1d1f', letterSpacing: '-0.3px', margin: 0 },
  subheading: { fontSize: '14px', color: '#86868b', marginTop: '4px', marginBottom: 0 },
  card: {
    background: '#fff',
    borderRadius: '16px',
    padding: '32px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 4px 20px rgba(0,0,0,0.06)',
  },
  label: {
    display: 'block',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.7px',
    color: '#86868b',
    marginBottom: '10px',
  },
  input: {
    width: '100%',
    fontSize: '17px',
    fontWeight: 500,
    padding: '12px 16px',
    border: '1.5px solid #e5e5ea',
    borderRadius: '10px',
    outline: 'none',
    color: '#1d1d1f',
    background: '#fafafa',
    fontFamily: 'inherit',
    transition: 'border-color 0.15s',
  },
  reasonInput: {
    width: '100%',
    fontSize: '14px',
    padding: '10px 14px',
    border: '1.5px solid #e5e5ea',
    borderRadius: '10px',
    outline: 'none',
    color: '#1d1d1f',
    background: '#fafafa',
    fontFamily: 'inherit',
    transition: 'border-color 0.15s',
  },
  divider: { height: '1px', background: '#f2f2f7', margin: '28px 0' },
  textarea: {
    width: '100%',
    minHeight: '260px',
    fontSize: '14px',
    lineHeight: '1.75',
    padding: '14px 16px',
    border: '1.5px solid #e5e5ea',
    borderRadius: '10px',
    outline: 'none',
    color: '#1d1d1f',
    resize: 'vertical',
    background: '#fafafa',
    fontFamily: 'inherit',
    transition: 'border-color 0.15s',
  },
};

// ─── Component ───────────────────────────────────────────────────────────────

export default function App() {
  const [lang, setLang] = useState('pt');
  const [scenario, setScenario] = useState(null);
  const [name, setName] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [copiedSubject, setCopiedSubject] = useState(false);
  const [copiedMessage, setCopiedMessage] = useState(false);
  const [focusedInput, setFocusedInput] = useState(null);

  const hasMessage = scenario !== null;
  const subject = hasMessage ? SUBJECTS[lang][scenario] : '';
  const showReason = scenario !== null && scenario !== 3;

  function regenerate(newLang, newScenario, newName, newReason) {
    if (newScenario === null) return;
    setMessage(buildMessage(newLang, newScenario, newName, newReason));
  }

  function handleLang(l) {
    setLang(l);
    if (scenario !== null) regenerate(l, scenario, name, reason);
  }

  function handleScenario(s) {
    setScenario(s);
    // Clear reason when switching to/from "next stage"
    const newReason = s === 3 ? '' : reason;
    if (s === 3) setReason('');
    regenerate(lang, s, name, newReason);
  }

  function handleName(e) {
    const n = e.target.value;
    setName(n);
    if (scenario !== null) regenerate(lang, scenario, n, reason);
  }

  function handleReason(e) {
    const r = e.target.value;
    setReason(r);
    if (scenario !== null) regenerate(lang, scenario, name, r);
  }

  function copyText(text, setter) {
    navigator.clipboard.writeText(text).then(() => {
      setter(true);
      setTimeout(() => setter(false), 1800);
    });
  }

  function inputBorder(id) {
    return focusedInput === id ? '#0071e3' : '#e5e5ea';
  }

  return (
    <div style={S.page}>
      <div style={S.inner}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <h1 style={S.heading}>Feedback Generator</h1>
          <p style={S.subheading}>Generate professional candidate messages in seconds</p>
        </div>

        <div style={S.card}>
          {/* ── Candidate name ── */}
          <div style={{ marginBottom: '24px' }}>
            <label htmlFor="candidateName" style={S.label}>Candidate name</label>
            <input
              id="candidateName"
              type="text"
              value={name}
              onChange={handleName}
              placeholder="e.g. Sofia Martins"
              autoComplete="off"
              style={{ ...S.input, borderColor: inputBorder('name') }}
              onFocus={() => setFocusedInput('name')}
              onBlur={() => setFocusedInput(null)}
            />
          </div>

          {/* ── Language toggle ── */}
          <div style={{ marginBottom: '24px' }}>
            <div style={S.label}>Language</div>
            <div style={{ display: 'inline-flex', background: '#f2f2f7', borderRadius: '10px', padding: '4px', gap: '4px' }}>
              {['pt', 'en'].map(l => (
                <button
                  key={l}
                  onClick={() => handleLang(l)}
                  style={{
                    padding: '8px 24px',
                    border: 'none',
                    borderRadius: '7px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    transition: 'all 0.15s',
                    background: lang === l ? '#fff' : 'transparent',
                    color: lang === l ? '#1d1d1f' : '#86868b',
                    boxShadow: lang === l ? '0 1px 3px rgba(0,0,0,0.12)' : 'none',
                  }}
                >
                  {l === 'pt' ? 'Português' : 'English'}
                </button>
              ))}
            </div>
          </div>

          {/* ── Scenario buttons ── */}
          <div style={{ marginBottom: showReason ? '24px' : '0' }}>
            <div style={S.label}>Feedback type</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {[1, 2, 3, 4].map(id => (
                <button
                  key={id}
                  onClick={() => handleScenario(id)}
                  style={{
                    padding: '13px 14px',
                    border: `1.5px solid ${scenario === id ? '#0071e3' : '#e5e5ea'}`,
                    borderRadius: '10px',
                    fontSize: '13.5px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    background: scenario === id ? '#e8f1fd' : '#fff',
                    color: scenario === id ? '#0071e3' : '#3a3a3c',
                    textAlign: 'left',
                    lineHeight: '1.4',
                    fontFamily: 'inherit',
                    transition: 'all 0.15s',
                  }}
                >
                  {SCENARIO_LABELS[lang][id]}
                </button>
              ))}
            </div>
          </div>

          {/* ── Optional reason (hidden for scenario 3) ── */}
          {showReason && (
            <div>
              <label htmlFor="reason" style={{ ...S.label, marginTop: 0 }}>
                Reason{' '}
                <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: '#aeaeb2' }}>
                  (optional)
                </span>
              </label>
              <input
                id="reason"
                type="text"
                value={reason}
                onChange={handleReason}
                placeholder={
                  lang === 'pt'
                    ? 'ex: procuravam mais experiência em gestão de equipas'
                    : 'e.g. they were looking for more experience in team management'
                }
                autoComplete="off"
                style={{ ...S.reasonInput, borderColor: inputBorder('reason') }}
                onFocus={() => setFocusedInput('reason')}
                onBlur={() => setFocusedInput(null)}
              />
            </div>
          )}

          <div style={S.divider} />

          {/* ── Generated message ── */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <div style={S.label}>Generated message</div>
              {hasMessage && (
                <div style={{ fontSize: '12px', color: '#aeaeb2' }}>{message.length} chars</div>
              )}
            </div>

            {!hasMessage ? (
              <div style={{ textAlign: 'center', padding: '52px 20px', color: '#aeaeb2', fontSize: '14px' }}>
                <div style={{ fontSize: '32px', marginBottom: '10px' }}>✉️</div>
                <div>Select a feedback type above to generate a message</div>
              </div>
            ) : (
              <>
                {/* Subject line display */}
                <div style={{
                  fontSize: '13px',
                  padding: '9px 13px',
                  background: '#f9f9fb',
                  borderRadius: '8px',
                  border: '1px solid #ebebf0',
                  marginBottom: '8px',
                  color: '#86868b',
                }}>
                  <span style={{ fontWeight: 600, color: '#3a3a3c' }}>Subject: </span>
                  {subject}
                </div>

                {/* Editable message */}
                <textarea
                  value={message}
                  onChange={e => {
                    setMessage(e.target.value);
                  }}
                  style={{
                    ...S.textarea,
                    borderColor: focusedInput === 'msg' ? '#0071e3' : '#e5e5ea',
                  }}
                  onFocus={() => setFocusedInput('msg')}
                  onBlur={() => setFocusedInput(null)}
                  spellCheck
                />
              </>
            )}

            {/* Copy buttons */}
            <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
              <button
                onClick={() => copyText(subject, setCopiedSubject)}
                disabled={!hasMessage}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: hasMessage ? 'pointer' : 'not-allowed',
                  background: copiedSubject ? '#34c759' : '#f2f2f7',
                  color: copiedSubject ? '#fff' : '#3a3a3c',
                  fontFamily: 'inherit',
                  opacity: hasMessage ? 1 : 0.38,
                  transition: 'all 0.15s',
                }}
              >
                {copiedSubject ? '✓ Copied!' : 'Copy subject'}
              </button>
              <button
                onClick={() => copyText(message, setCopiedMessage)}
                disabled={!hasMessage}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: hasMessage ? 'pointer' : 'not-allowed',
                  background: copiedMessage ? '#34c759' : '#0071e3',
                  color: '#fff',
                  fontFamily: 'inherit',
                  opacity: hasMessage ? 1 : 0.38,
                  transition: 'all 0.15s',
                }}
              >
                {copiedMessage ? '✓ Copied!' : 'Copy message'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
