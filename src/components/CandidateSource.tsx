import { useEffect, useRef, useState } from "react";
import { Upload, Layers, ArrowRight } from "lucide-react";
import { type FilterInput } from "../domain/pick5";
import {
  parseCandidates,
  setOperation,
  type SetOperation,
} from "../lib/candidates";
import { download } from "../lib/plans";
export default function CandidateSource({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const [text, setText] = useState(""),
    [operand, setOperand] = useState(""),
    [operation, setOperationMode] = useState<SetOperation>("intersection"),
    [error, setError] = useState(""),
    [preview, setPreview] = useState<string[] | null>(null),
    [notice, setNotice] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const editor = useRef<HTMLTextAreaElement>(null);
  const details = useRef<HTMLDetailsElement>(null);
  const lastLoaded = useRef(input.candidates);
  const generation = useRef(0);
  const latest = useRef(input);
  latest.current = input;
  useEffect(() => {
    if (input.candidates) lastLoaded.current = input.candidates;
    setPreview(null);
    generation.current++;
  }, [input.candidates]);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  const load = () => {
    generation.current++;
    try {
      const list = parseCandidates(text);
      onChange({ ...latest.current, candidates: list });
      setError("");
      setNotice(`已载入${list.length.toLocaleString()}组去重号码`);
    } catch (e) {
      setNotice("");
      setError((e as Error).message);
      editor.current?.focus();
    }
  };
  const run = () => {
    try {
      if (!input.candidates?.length)
        throw new Error("请先载入外部大底作为集合A");
      setPreview(
        setOperation(input.candidates, parseCandidates(operand), operation),
      );
      setError("");
    } catch (e) {
      setError((e as Error).message);
      setPreview(null);
    }
  };
  return (
    <section className="card source-card">
      <div className="section-head">
        <h2>
          <Layers size={17} />
          候选来源
        </h2>
        <div className="source-toggle">
          <button
            className={!input.candidates ? "active" : ""}
            onClick={() => {
              generation.current++;
              onChange({ ...input, candidates: undefined });
              setPreview(null);
              setError("");
              setNotice("已切换为定位复式；已载入的大底可点击外部大底恢复。");
            }}
          >
            定位复式
          </button>
          <button
            className={input.candidates ? "active" : ""}
            onClick={() => {
              if (details.current) details.current.open = true;
              setError("");
              if (lastLoaded.current) {
                onChange({ ...latest.current, candidates: lastLoaded.current });
                setNotice(`已恢复${lastLoaded.current.length.toLocaleString()}组大底号码`);
              } else {
                setNotice("请先在下方粘贴五位号码，或点击导入 TXT，再载入大底。灰色文字仅为格式示例。");
              }
              editor.current?.focus();
            }}
          >
            外部大底
          </button>
        </div>
      </div>
      {notice && <p className="notice small" role="status">{notice}</p>}
      <details ref={details} open={Boolean(input.candidates)}>
        <summary>
          导入大底与集合运算{" "}
          <span>
            {input.candidates
              ? `${input.candidates.length.toLocaleString()}组`
              : "支持TXT、空格或逗号分隔"}
          </span>
        </summary>
        <div className="source-body">
          <p className="muted small">
            外部大底载入后独立作为候选集，不与上方定位选择混合。号码必须为五位，前导零保留。
          </p>
          <label className="field-label">
            集合A号码
            <textarea
              ref={editor}
              aria-label="大底号码"
              aria-invalid={Boolean(error)}
              aria-describedby="candidate-input-help candidate-input-error"
              value={text}
              placeholder={"00127\n01234\n99999"}
              onChange={(e) => setText(e.target.value)}
              rows={4}
            />
          </label>
          <p id="candidate-input-help" className="muted small">先粘贴或导入实际号码；输入框内的灰色号码只是格式示例。</p>
          <p id="candidate-input-error" className="validation" role={error ? "alert" : undefined}>{error}</p>
          <div className="head-actions">
            <button
              className="button secondary"
              onClick={() => file.current?.click()}
            >
              <Upload size={14} />
              导入 TXT
            </button>
            <button className="button primary" onClick={load}>
              载入大底 <ArrowRight size={14} />
            </button>
            <input
              ref={file}
              hidden
              type="file"
              accept=".txt,.csv,text/plain,text/csv"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                const token = ++generation.current;
                try {
                  if (f.size > 10 * 1024 * 1024)
                    throw new Error("文件不可超过10MiB");
                  const raw = await f.text();
                  const list = parseCandidates(raw);
                  if (token !== generation.current) return;
                  setText(raw);
                  onChange({ ...latest.current, candidates: list });
                  setError("");
                  setNotice(`已载入${list.length.toLocaleString()}组去重号码`);
                } catch (err) {
                  if (token === generation.current)
                    setError((err as Error).message);
                } finally {
                  if (file.current) file.current.value = "";
                }
              }}
            />
          </div>
          <details className="set-details">
            <summary>集合运算：当前大底为A，另输入B</summary>
            <label className="field-label">
              集合B号码
              <textarea
                aria-label="集合B号码"
                value={operand}
                onChange={(e) => {
                  setOperand(e.target.value);
                  setPreview(null);
                }}
                rows={3}
                placeholder="每行一个五位号码"
              />
            </label>
            <div className="head-actions">
              <select
                aria-label="集合运算类型"
                value={operation}
                onChange={(e) => {
                  setOperationMode(e.target.value as SetOperation);
                  setPreview(null);
                }}
              >
                <option value="intersection">交集 A∩B</option>
                <option value="union">并集 A∪B</option>
                <option value="difference">差集 A减B</option>
                <option value="symmetric">对称差 A△B</option>
              </select>
              <button className="button secondary" onClick={run}>
                预览集合结果
              </button>
            </div>
            {preview && (
              <div className="set-preview">
                <strong>结果共{preview.length.toLocaleString()}组</strong>
                <p>
                  {preview.slice(0, 8).join(" · ")}
                  {preview.length > 8 ? " …" : ""}
                </p>
                <div className="head-actions">
                  <button
                    className="button primary"
                    disabled={!preview.length}
                    onClick={() => {
                      onChange({ ...input, candidates: preview });
                      setText(preview.join("\n"));
                      setPreview(null);
                      setNotice("集合结果已作为新的大底");
                    }}
                  >
                    替换集合A
                  </button>
                  <button
                    className="button secondary"
                    onClick={() =>
                      download("pl5-集合结果.txt", preview.join("\n"))
                    }
                  >
                    导出结果
                  </button>
                </div>
                {preview.length === 0 && (
                  <p>空集合可导出，不作为可计算大底载入。</p>
                )}
              </div>
            )}
          </details>
        </div>
      </details>
    </section>
  );
}
