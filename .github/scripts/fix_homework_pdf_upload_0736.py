from pathlib import Path

EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

anchor = '''  ["homeworkCameraInput","homeworkFileInput"].forEach(function(id){\n    const input = document.getElementById(id);\n    if(!input){\n      return;\n    }\n\n    input.addEventListener("change", function(event){\n      const file = event.target.files?.[0];\n      if(!file){\n        return;\n      }\n\n      showHomeworkLessonWorkspace({keepPreview:true});\n      showHomeworkPreview(file);\n    }, true);\n  });\n'''

replacement = r'''  let homeworkPdfJsPromise = null;

  function loadHomeworkPdfJs(){
    if(window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if(homeworkPdfJsPromise) return homeworkPdfJsPromise;

    homeworkPdfJsPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.async = true;
      script.onload = () => {
        if(!window.pdfjsLib){
          reject(new Error("PDF.js loaded without pdfjsLib"));
          return;
        }
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
          "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        resolve(window.pdfjsLib);
      };
      script.onerror = () => reject(new Error("Failed to load PDF.js"));
      document.head.appendChild(script);
    });

    return homeworkPdfJsPromise;
  }

  async function convertHomeworkPdfFirstPageToImage(file){
    const pdfjs = await loadHomeworkPdfJs();
    const bytes = new Uint8Array(await file.arrayBuffer());
    const pdf = await pdfjs.getDocument({data:bytes}).promise;
    if(!pdf.numPages){
      throw new Error("PDF has no pages");
    }

    const page = await pdf.getPage(1);
    const baseViewport = page.getViewport({scale:1});
    const maxSide = 1800;
    const scale = Math.min(
      2.2,
      maxSide / Math.max(baseViewport.width, baseViewport.height)
    );
    const viewport = page.getViewport({scale:Math.max(1.25, scale)});

    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d", {alpha:false});
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    await page.render({canvasContext:ctx, viewport}).promise;

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        result => result ? resolve(result) : reject(new Error("PDF canvas conversion failed")),
        "image/jpeg",
        0.92
      );
    });

    const baseName = String(file.name || "homework.pdf").replace(/\.pdf$/i, "");
    return new File([blob], `${baseName}-page-1.jpg`, {type:"image/jpeg"});
  }

  async function handleHomeworkPdfUpload(file){
    showHomeworkLessonWorkspace({keepPreview:true});

    const stage = document.querySelector(".lesson-visual-stage");
    if(stage){
      stage.innerHTML = `
        <div class="homework-stage-shell">
          <section class="homework-upload-card" style="min-height:280px">
            <div class="homework-upload-icon">PDF</div>
            <h2>קוראת את קובץ ה־PDF</h2>
            <p>אני ממירה את העמוד הראשון לתמונה כדי לזהות את התרגיל.</p>
          </section>
        </div>`;
    }

    try{
      const imageFile = await convertHomeworkPdfFirstPageToImage(file);
      showHomeworkPreview(imageFile);

      if(typeof window.handleHomeworkFile === "function"){
        await window.handleHomeworkFile(imageFile);
      }
      else if(typeof handleHomeworkFile === "function"){
        await handleHomeworkFile(imageFile);
      }
      else{
        throw new Error("handleHomeworkFile is not available");
      }
    }
    catch(error){
      console.error("HOMEWORK PDF UPLOAD FAILED:", error);
      if(typeof window.renderHomeworkStructuredTeacherMessage === "function"){
        await window.renderHomeworkStructuredTeacherMessage(
          "לא הצלחתי לקרוא את קובץ ה־PDF. נסי לשמור אותו כתמונה או לצלם את העמוד."
        );
      }
      else if(typeof addMessage === "function"){
        addMessage("assistant", "לא הצלחתי לקרוא את קובץ ה־PDF. נסי לשמור אותו כתמונה או לצלם את העמוד.");
      }
    }
  }

  ["homeworkCameraInput","homeworkFileInput"].forEach(function(id){
    const input = document.getElementById(id);
    if(!input){
      return;
    }

    // The file picker supports both images and PDFs. Camera remains image-first.
    if(id === "homeworkFileInput"){
      input.setAttribute("accept", "image/*,application/pdf,.pdf");
    }

    input.addEventListener("change", function(event){
      const file = event.target.files?.[0];
      if(!file){
        return;
      }

      const isPdf =
        String(file.type || "").toLowerCase() === "application/pdf"
        || /\.pdf$/i.test(String(file.name || ""));

      if(isPdf){
        // Stop the legacy image-only handler from trying to compress a PDF.
        event.preventDefault();
        event.stopImmediatePropagation();
        handleHomeworkPdfUpload(file);
        return;
      }

      showHomeworkLessonWorkspace({keepPreview:true});
      showHomeworkPreview(file);
    }, true);
  });
'''

if anchor not in ext:
    raise SystemExit('homework input listener anchor not found')
ext = ext.replace(anchor, replacement, 1)

# Export the structured renderer so the PDF error path can use the same dark UI.
if 'window.renderHomeworkStructuredTeacherMessage' not in ext:
    pass

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.35";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.36";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0735', '/he/workspace/lesson-completion-core.js?v=0736')

index = index.replace('IAKIDS • build 0.7.35', 'IAKIDS • build 0.7.36')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.35";', 'window.IAKIDS_BUILD_VERSION = "0.7.36";')
index = index.replace('/he/workspace/lesson-completion.js?v=0735', '/he/workspace/lesson-completion.js?v=0736')

EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('PDF homework upload enabled via first-page PDF.js conversion; build 0.7.36')
