import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChefHat,
  ClipboardList,
  FileImage,
  Loader2,
  RefreshCw,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

type Ingredient = {
  name: string;
  quantity?: string | null;
};

type Recipe = {
  name: string;
  ingredients: string[];
  instructions: string[];
};

type Recommendation = {
  recipe: Recipe;
  matched_ingredients: string[];
  missing_ingredients: string[];
  score: number;
};

type RefinedRecipe = {
  best_match?: string | null;
  instructions?: string[];
  substitutions?: Record<string, string>;
  shopping_list?: string[];
  status?: string;
};

type PipelineResult = {
  photo?: {
    filename?: string | null;
    ingredients?: Ingredient[];
    status?: string;
  };
  recommendations?: Recommendation[];
  refined_recipe?: RefinedRecipe;
  status?: string;
};

type TaskStatus = {
  task_id: string;
  status: string;
  result?: PipelineResult | null;
  error_code?: string | null;
  error?: string | null;
};

type UploadState = "idle" | "uploading" | "queued" | "complete" | "failed";

const POLL_INTERVAL_MS = 1200;

function getTaskFailureMessage(task: TaskStatus) {
  if (task.error_code && task.error) {
    return `${task.error_code}: ${task.error}`;
  }
  if (task.error_code) {
    return `${task.error_code}: We could not finish this recipe right now.`;
  }

  const error = task.error?.trim();
  if (error?.includes("Gemini quota reached") || error?.includes("RESOURCE_EXHAUSTED")) {
    return "AI_QUOTA_REACHED: AI recipe generation is temporarily unavailable because the Gemini quota has been reached. Please try again after the quota resets.";
  }
  return error ? `TASK_FAILED: ${error}` : "TASK_FAILED: We could not finish this recipe right now.";
}

function getResultFailureMessage(result: PipelineResult) {
  const status = result.refined_recipe?.status ?? result.photo?.status ?? result.status;

  if (status === "unsupported_file_type") {
    return "UNSUPPORTED_FILE_TYPE: Please upload a fridge or pantry photo.";
  }
  if (status === "empty_file") {
    return "EMPTY_FILE: The uploaded file was empty. Please choose another photo.";
  }
  if (status === "ai_not_configured") {
    return "AI_NOT_CONFIGURED: Recipe generation needs a Gemini API key before it can write a personalized recipe.";
  }
  if (status && status !== "refined" && status !== "matched" && status !== "received") {
    return `${status.toUpperCase()}: We could not finish this recipe right now.`;
  }

  if (!result.refined_recipe) {
    return "RECIPE_GENERATION_INCOMPLETE: The photo was processed, but no final recipe was returned.";
  }

  return null;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!task || task.result || task.error || uploadState !== "queued") {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/tasks/${task.task_id}`);
        if (!response.ok) {
          throw new Error("Could not check your recipe yet.");
        }

        const nextTask = (await response.json()) as TaskStatus;
        setTask(nextTask);

        if (nextTask.error || nextTask.status === "FAILURE") {
          setUploadState("failed");
          setMessage(getTaskFailureMessage(nextTask));
        } else if (nextTask.result) {
          const resultError = getResultFailureMessage(nextTask.result);
          if (resultError) {
            setUploadState("failed");
            setMessage(resultError);
          } else {
            setUploadState("complete");
            setMessage("Your recipe is ready.");
          }
        }
      } catch (error) {
        setUploadState("failed");
        setMessage(error instanceof Error ? error.message : "We could not check your recipe yet.");
      }
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [task, uploadState]);

  const result = task?.result ?? null;
  const ingredients = result?.photo?.ingredients ?? [];
  const recommendations = result?.recommendations ?? [];
  const refinedRecipe = result?.refined_recipe;
  const topRecipe = recommendations[0];
  const shoppingList = refinedRecipe?.shopping_list ?? topRecipe?.missing_ingredients ?? [];
  const isWorking = uploadState === "uploading" || uploadState === "queued";

  const progressSteps = useMemo(
    () => [
      {
        label: "Reading photo",
        done: ingredients.length > 0,
        active: uploadState !== "idle",
      },
      {
        label: "Finding recipes",
        done: recommendations.length > 0,
        active: uploadState === "queued" || uploadState === "complete",
      },
      {
        label: "Writing plan",
        done: Boolean(refinedRecipe),
        active: uploadState === "queued" || uploadState === "complete",
      },
    ],
    [ingredients.length, recommendations.length, refinedRecipe, uploadState],
  );

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setTask(null);
    setMessage("");
    setUploadState("idle");

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setMessage("Choose a fridge photo first.");
      return;
    }

    setUploadState("uploading");
    setMessage("Uploading your photo...");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/fridge-photo", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error("Upload failed.");
      }

      const submission = (await response.json()) as TaskStatus;
      setTask(submission);
      setUploadState("queued");
      setMessage("Looking for a good dinner match...");
    } catch (error) {
      setUploadState("failed");
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  function resetUpload() {
    setSelectedFile(null);
    setTask(null);
    setPreviewUrl(null);
    setUploadState("idle");
    setMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <main className="app-shell">
      <section className="app-frame">
        <div className="brand-bar">
          <div className="brand-lockup">
            <span className="brand-mark">
              <ChefHat size={24} aria-hidden="true" />
            </span>
            <div>
              <h1>SmartFridge</h1>
              <p>Fridge-to-recipe recommendations</p>
            </div>
          </div>
          <button className="ghost-button" type="button" onClick={resetUpload}>
            <RefreshCw size={17} />
            Start over
          </button>
        </div>

        <section className="recipe-workspace">
          <aside className="photo-card">
            <form className="upload-form" onSubmit={handleSubmit}>
              <button
                className="photo-drop"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                aria-label="Choose fridge photo"
              >
                {previewUrl ? (
                  <img src={previewUrl} alt="Selected fridge preview" />
                ) : (
                  <span className="empty-preview">
                    <FileImage size={36} aria-hidden="true" />
                    <strong>Choose fridge photo</strong>
                  </span>
                )}
              </button>

              <input
                ref={fileInputRef}
                className="file-input"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
              />

              <div className="selected-file">
                <span>{selectedFile?.name ?? "No photo selected"}</span>
                {selectedFile ? (
                  <button type="button" className="icon-button" onClick={resetUpload} aria-label="Clear photo">
                    <X size={17} aria-hidden="true" />
                  </button>
                ) : null}
              </div>

              <button className="primary-button" type="submit" disabled={!selectedFile || isWorking}>
                {isWorking ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <UploadCloud size={18} />}
                {isWorking ? "Cooking up ideas" : "Find recipes"}
              </button>
            </form>

            <div className={`friendly-status ${uploadState}`}>
              {uploadState === "failed" ? <AlertCircle size={18} /> : <Sparkles size={18} />}
              <span>{message || "Ready when your fridge is."}</span>
            </div>

            <div className="progress-strip" aria-label="Recipe progress">
              {progressSteps.map((step) => (
                <div className={`progress-step ${step.active ? "active" : ""} ${step.done ? "done" : ""}`} key={step.label}>
                  <span>{step.done ? <CheckCircle2 size={16} /> : null}</span>
                  <small>{step.label}</small>
                </div>
              ))}
            </div>
          </aside>

          <section className="recipe-card">
            <div className="recipe-heading">
              <span className="eyebrow">{uploadState === "complete" ? "Dinner idea" : "Recipe preview"}</span>
              <h2>{refinedRecipe?.best_match || topRecipe?.recipe.name || "What should we make tonight?"}</h2>
            </div>

            {refinedRecipe ? (
              <RecipePlan recipe={refinedRecipe} />
            ) : (
              <div className="recipe-placeholder">
                <ChefHat size={42} />
                <p>Your personalized recipe will appear here after the photo is analyzed.</p>
              </div>
            )}
          </section>

          <section className="pantry-card">
            <SectionHeader icon={<ClipboardList size={18} />} title="Found in your fridge" count={ingredients.length} />
            {ingredients.length > 0 ? (
              <div className="ingredient-grid">
                {ingredients.map((ingredient, index) => (
                  <span className="ingredient-pill" key={`${ingredient.name}-${index}`}>
                    {ingredient.name}
                  </span>
                ))}
              </div>
            ) : (
              <EmptyState text="Ingredients will appear after analysis." />
            )}
          </section>

          <section className="shopping-card">
            <SectionHeader icon={<Sparkles size={18} />} title="Still need" count={shoppingList.length} />
            {shoppingList.length > 0 ? (
              <ul className="shopping-list">
                {shoppingList.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <EmptyState text="Missing items will appear here." />
            )}
          </section>

          <section className="matches-card">
            <SectionHeader icon={<ChefHat size={18} />} title="Other good matches" count={recommendations.length} />
            {recommendations.length > 0 ? (
              <div className="match-list">
                {recommendations.map((recommendation) => (
                  <RecipeMatch recommendation={recommendation} key={recommendation.recipe.name} />
                ))}
              </div>
            ) : (
              <EmptyState text="Recipe matches will appear after search." />
            )}
          </section>
        </section>
      </section>
    </main>
  );
}

function SectionHeader({ icon, title, count }: { icon: ReactNode; title: string; count: number }) {
  return (
    <div className="section-header">
      <div>
        {icon}
        <h3>{title}</h3>
      </div>
      <span>{count}</span>
    </div>
  );
}

function RecipePlan({ recipe }: { recipe: RefinedRecipe }) {
  const substitutions = Object.entries(recipe.substitutions ?? {});

  return (
    <div className="recipe-plan">
      <ol className="instruction-list">
        {(recipe.instructions ?? []).map((step, index) => (
          <li key={`${step}-${index}`}>
            <span>{index + 1}</span>
            <p>{step}</p>
          </li>
        ))}
      </ol>

      {substitutions.length > 0 ? (
        <div className="substitution-box">
          <h3>Smart swaps</h3>
          <div>
            {substitutions.map(([original, substitute]) => (
              <p key={original}>
                <span>{original}</span>
                <ArrowRight size={14} />
                <strong>{substitute}</strong>
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RecipeMatch({ recommendation }: { recommendation: Recommendation }) {
  return (
    <article className="match-card">
      <div>
        <h4>{recommendation.recipe.name}</h4>
        <p>{Math.round(recommendation.score * 100)}% match</p>
      </div>
      <div className="match-tags">
        {recommendation.matched_ingredients.slice(0, 4).map((ingredient) => (
          <span key={ingredient}>{ingredient}</span>
        ))}
      </div>
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

export default App;
