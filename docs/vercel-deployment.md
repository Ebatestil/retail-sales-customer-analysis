# Deploy the report on Vercel

This project deploys the existing report as a static site. Vercel runs a small Node.js packaging script; Python, a database server and environment variables are unnecessary for hosting.

## GitHub deployment

1. Commit and push `package.json`, `vercel.json`, `scripts/build_static.mjs`, `.gitignore`, `.vercelignore` and this guide to the repository, along with the existing report and its supporting files.
2. Open https://vercel.com/new, sign in, and import `Ebatestil/retail-sales-customer-analysis`.
3. Use these settings (the repository configuration supplies them):

| Setting | Value |
|---|---|
| Framework Preset | Other |
| Root Directory | Repository root (`./`) |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | Empty / skip |
| Environment Variables | None |

4. Click **Deploy**. Once the deployment is ready, open its production URL and check the report and supporting links.
5. Use the assigned production URL for a **View analysis report** link in your portfolio. The exact hostname is assigned by Vercel; do not assume one before deployment.

## Local verification

Run `npm run build`. All local report links must exist and `outputs/validation.json` must show `passed`.
Serve `dist/` with any static HTTP server, for example `python -m http.server 8766 --directory dist`, and open http://localhost:8766.

The package includes the HTML report, its directly linked evidence files, and the Poppins license. The root URL opens the report directly. The original `/reports/retail_analysis.html` path also works. Raw source tables, the SQLite database, and the large prepared fact tables are outside the public output.

The supporting Markdown files can be viewed or downloaded as source documents. Poppins and all six charts are embedded in the HTML.

## Updates

After changing the analysis, run the Python analysis and report scripts locally, review the results, and commit the updated report and evidence. Push to the connected production branch to trigger Vercel's next build.

References: [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json), [configuring a build](https://vercel.com/docs/builds/configure-a-build).
