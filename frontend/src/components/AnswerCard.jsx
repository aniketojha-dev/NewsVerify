import React, { useState } from 'react'

function getBadgeClass(status) {
  const s = (status || '').toLowerCase()
  if (s.includes('verified') && !s.includes('likely')) return 'badge-verified'
  if (s.includes('likely') || s.includes('high')) return 'badge-likely'
  if (s.includes('low') || s.includes('not')) return 'badge-low'
  return 'badge-unsupported'
}

function getBarColor(score) {
  if (score >= 85) return '#4D8C67'
  if (score >= 60) return '#C4941A'
  return '#C62828'
}

export default function AnswerCard({ data, onNewSearch }) {
  const [showDetails, setShowDetails] = useState(false)

  const {
    title,
    short_answer,
    answer,
    evidence,
    why_this_result,
    key_details,
    confidence_score,
    confidence,
    verification_status,
    sources,
    category,
    year,
    source_type,
    related_topics,
  } = data

  const hasBadgeCheck = verification_status?.toLowerCase().includes('verified')
  const showEvidence = evidence && evidence !== short_answer && evidence.length > short_answer.length

  const factDetails = key_details ? key_details.filter(d => d.label === 'Fact') : []

  return (
    <div className="answer-card">
      {/* LEFT — Verification Report */}
      <div className="answer-left">
        <div className="badge-row">
          <span className={`badge ${getBadgeClass(verification_status)}`}>
            {hasBadgeCheck && <span className="badge-check">&#10003;</span>}
            {verification_status || 'Analyzed'}
          </span>
          {sources && sources.length > 0 && (
            <span className="badge-sub">
              Cross-verified by {sources.length} trusted source{sources.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {title && (
          <div>
            <div className="answer-title">{title}</div>
          </div>
        )}

        <div>
          <div className="section-label">Summary</div>
          <div className="answer-summary">{short_answer}</div>
        </div>

        {factDetails.length > 0 && (
          <div>
            <div className="section-label">Key Facts</div>
            <div className="key-facts-list">
              {factDetails.map((d, i) => (
                <div className="key-fact-item" key={i}>
                  <span className="key-fact-bullet">&#8212;</span>
                  <span>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {sources && sources.length > 0 && (
          <div>
            <div className="section-label">Trusted Sources</div>
            <div className="source-refs" style={{ borderTop: 'none', paddingTop: 0 }}>
              {sources.map((s, i) => (
                <span key={i} onClick={() => onNewSearch(`news from ${s}`)}>
                  [{i + 1}] {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {why_this_result && why_this_result.length > 0 && (
          <div style={{ flexShrink: 0 }}>
            <button
              onClick={() => setShowDetails(!showDetails)}
              style={{
                border: 'none',
                background: 'transparent',
                color: '#A69E94',
                fontSize: '13px',
                cursor: 'pointer',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontFamily: 'inherit',
              }}
            >
              {showDetails ? 'Hide verification details' : 'Why this result'}
              <span style={{
                transform: showDetails ? 'rotate(180deg)' : 'none',
                display: 'inline-block',
                transition: 'transform 0.15s',
                fontSize: '10px',
              }}>&#9660;</span>
            </button>
            {showDetails && (
              <div style={{
                marginTop: '8px',
                background: '#F6F2EC',
                borderRadius: '10px',
                padding: '12px 14px',
              }}>
                {why_this_result.map((w, i) => (
                  <div key={i} style={{
                    fontSize: '13px',
                    color: '#5B5651',
                    lineHeight: '1.6',
                    paddingLeft: '12px',
                    position: 'relative',
                  }}>
                    <span style={{ position: 'absolute', left: 0, color: '#7B8EE0' }}>&bull;</span>
                    {w}
                  </div>
                ))}
                {showEvidence && (
                  <div style={{
                    fontSize: '13px',
                    color: '#5B5651',
                    lineHeight: '1.5',
                    marginTop: '8px',
                    padding: '8px 10px',
                    background: '#FBF9F5',
                    borderRadius: '8px',
                  }}>
                    {evidence}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* RIGHT — Sidebar */}
      <div className="answer-right">
        <div>
          <div className="right-section-title">Confidence</div>
          <div className="confidence-score">{confidence_score || 0}%</div>
          <div className="confidence-label">
            {confidence === 'high' ? 'High Confidence' : confidence === 'medium' ? 'Medium Confidence' : 'Low Confidence'}
          </div>
          <div className="confidence-bar-bg">
            <div className="confidence-bar-fill"
              style={{ width: `${confidence_score || 0}%`, background: getBarColor(confidence_score || 0) }}
            />
          </div>
          <div className="confidence-note">
            {confidence_score >= 85
              ? 'Cross-referenced across multiple trusted sources'
              : confidence_score >= 60
              ? 'Partially corroborated by available sources'
              : 'Limited source corroboration'}
          </div>
        </div>

        {sources && sources.length > 0 && (
          <div>
            <div className="right-section-title">Sources</div>
            <div>
              {sources.map((s, i) => (
                <span className="source-pill" key={i} onClick={() => onNewSearch(`news from ${s}`)}>{s}</span>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="right-section-title">Coverage</div>
          <div className="meta-minimal">
            {year && <span className="meta-tag">{year}</span>}
            {category && <span className="meta-tag">{category}</span>}
            <span className="meta-tag">{source_type === 'live' ? 'Live Search' : 'Knowledge Base'}</span>
          </div>
        </div>

        {related_topics && related_topics.length > 0 && (
          <div>
            <div className="right-section-title">Related</div>
            <div>
              {related_topics.map((t, i) => (
                <button className="related-chip" key={i} onClick={() => onNewSearch(t)}>{t}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
