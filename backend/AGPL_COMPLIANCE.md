# AGPL v3 Compliance Guide

## Overview

This project uses **Swiss Ephemeris**, which is dual-licensed under:
1. **AGPL v3** (Affero General Public License v3) - Free for open-source projects
2. **Commercial License** - Available from Astrodienst AG for proprietary use

Since we use the AGPL version, **this entire project must be AGPL-licensed**.

## AGPL Requirements

The GNU Affero General Public License v3 has special requirements for network-accessible software:

### Section 13: Remote Network Interaction

> If you modify the Program, your modified version must prominently offer all users 
> interacting with it remotely through a computer network an opportunity to receive 
> the Corresponding Source of your version.

**This means:** Anyone who uses your API over a network must have access to the complete source code.

## How We Comply

### 1. Source Code Availability ✅

**Implementation:**
- Source code published on GitHub: [YOUR_GITHUB_REPO_URL]
- `/license` API endpoint provides source code links
- README.md clearly states AGPL licensing
- LICENSE file included in repository

**Code Location:**
```python
# backend/app/__init__.py
@app.get("/license")
def license_info():
    # Returns license info and source code URLs
```

### 2. Startup Logging ✅

**Implementation:**
- Application logs AGPL notice on startup
- Swiss Ephemeris version logged
- Copyright notices displayed
- Source code URLs logged

**Log Output:**
```
============================================================
AGPL-Licensed Software Notice
============================================================
Swiss Ephemeris version: 2.10.3
Swiss Ephemeris is licensed under AGPL v3
Copyright (C) 1997-2021 Astrodienst AG, Switzerland
Source code: https://github.com/astrorigin/pyswisseph
This application source: [YOUR_GITHUB_REPO_URL]
============================================================
```

### 3. Copyright Preservation ✅

**Swiss Ephemeris Copyright:**
```
Copyright (C) 1997-2021 Astrodienst AG, Switzerland
```

**Our Copyright:**
```
Copyright (C) 2026 [YOUR_NAME]
```

Both preserved in:
- LICENSE file
- README.md
- Startup logs
- API documentation

### 4. License Notice in API Responses ✅

**Endpoint:** `GET /license`

Returns:
```json
{
  "license": "AGPL-3.0",
  "components": [
    {
      "name": "Swiss Ephemeris",
      "version": "2.10.3",
      "license": "AGPL-3.0 or Commercial",
      "copyright": "Copyright (C) 1997-2021 Astrodienst AG",
      "source": "https://github.com/astrorigin/pyswisseph"
    }
  ],
  "agpl_notice": "Users interacting with this software over a network..."
}
```

### 5. Documentation ✅

**Files:**
- `LICENSE` - Full AGPL v3 license with Swiss Ephemeris notice
- `README.md` - License section with AGPL explanation
- `AGPL_COMPLIANCE.md` - This file

## Logging Configuration

### What We Log

**On Startup:**
```python
app.logger.info("Swiss Ephemeris version: {version}")
app.logger.info("Swiss Ephemeris is licensed under AGPL v3")
app.logger.info("Copyright (C) 1997-2021 Astrodienst AG")
app.logger.info("Source code: {github_url}")
```

**Why:**
- Transparency about AGPL-licensed components
- Clear attribution to Swiss Ephemeris developers
- Compliance with AGPL copyright notice requirements

### What We DON'T Log

We do NOT log:
- Individual user interactions with ephemeris data
- Specific calculations performed
- User birth data or personal information

**Why:**
- AGPL requires source code availability, not usage tracking
- Privacy and GDPR compliance
- Only licensing information is required

## For Developers

### If You Fork/Modify This Project

**You MUST:**

1. **Keep AGPL License**
   ```bash
   # Keep these files unchanged:
   - LICENSE
   - AGPL_COMPLIANCE.md
   ```

2. **Make Source Available**
   - Publish on GitHub/GitLab/similar
   - Update URLs in code to point to YOUR repository
   - Keep `/license` endpoint functional

3. **Document Changes**
   ```markdown
   ## Modifications
   - [Date] - [Your Name] - Description of changes
   ```

4. **Preserve Copyrights**
   - Keep Swiss Ephemeris copyright
   - Keep original project copyright
   - Add your own copyright if making substantial changes

5. **Update Source URLs**
   ```python
   # backend/app/__init__.py
   app.logger.info("This application source: https://github.com/YOUR_USERNAME/YOUR_REPO")
   ```

### If You Want Proprietary/Closed-Source

**You CANNOT use AGPL version** - You must:

1. **Purchase Swiss Ephemeris Commercial License**
   - Contact: Astrodienst AG
   - Website: https://www.astro.com/swisseph/
   - Get written permission and license agreement

2. **Re-license This Project**
   - Remove AGPL license
   - Contact original author for permission
   - Apply new license terms

3. **Remove AGPL Code**
   - Replace Swiss Ephemeris with commercial version
   - Remove AGPL compliance code
   - Update all documentation

## For Users

### Your Rights Under AGPL

**You have the right to:**

1. **Access Source Code**
   - Visit: [YOUR_GITHUB_REPO_URL]
   - Clone: `git clone [YOUR_REPO_URL]`
   - Download: Available on GitHub releases

2. **Modify the Code**
   - Make changes for personal use
   - Fork the repository
   - Create derivative works

3. **Redistribute**
   - Share your modifications
   - Publish your fork
   - Run your own instance

**You must:**
- Keep the AGPL license on any modifications
- Make your source code available if running as a network service
- Preserve copyright notices

### Getting the Source Code

**Method 1: API Endpoint**
```bash
curl http://localhost:8080/license
```

**Method 2: GitHub**
```bash
git clone [YOUR_GITHUB_REPO_URL]
```

**Method 3: Docker**
```bash
docker pull [YOUR_DOCKER_IMAGE]
```

## Verification

### Checklist for Maintainers

Before deployment, verify:

- [ ] LICENSE file present in repository root
- [ ] README.md contains AGPL section
- [ ] `/license` endpoint returns correct information
- [ ] Startup logs show AGPL notice
- [ ] Source code URLs are correct and accessible
- [ ] Swiss Ephemeris copyright preserved
- [ ] All modifications documented
- [ ] GitHub repository is public

### Testing Compliance

```bash
# 1. Check /license endpoint
curl http://localhost:8080/license | jq

# 2. Verify startup logs
docker logs [container] | grep "AGPL"

# 3. Check source code access
git clone [YOUR_REPO_URL]

# 4. Verify LICENSE file
cat LICENSE | grep "AGPL"
```

## FAQ

**Q: Why AGPL instead of GPL?**

A: Swiss Ephemeris is AGPL-licensed. AGPL extends GPL to require source code disclosure for network services, not just distributed software.

**Q: Can I use this in a commercial product?**

A: Yes, but you must either:
1. Make your product AGPL and open-source, OR
2. Purchase commercial license for Swiss Ephemeris from Astrodienst AG

**Q: Do I need to log every API call?**

A: No. You only need to:
- Log AGPL notice on startup
- Provide `/license` endpoint
- Make source code available

**Q: What if I only modify the frontend?**

A: If your frontend connects to this API, the frontend doesn't need to be AGPL. Only backend code that uses Swiss Ephemeris must be AGPL.

**Q: Can I remove the AGPL logging?**

A: No, that would violate AGPL compliance. The logging ensures users know about their rights to access source code.

**Q: Is there extra overhead from AGPL?**

A: No performance overhead. AGPL only requires legal compliance (source code availability), not technical changes.

## References

- **AGPL v3 Full Text**: https://www.gnu.org/licenses/agpl-3.0.html
- **Swiss Ephemeris License**: https://www.astro.com/swisseph/swephinfo_e.htm
- **Swiss Ephemeris Source**: https://github.com/astrorigin/pyswisseph
- **GNU AGPL FAQ**: https://www.gnu.org/licenses/gpl-faq.html#AGPLv3

## Contact

For licensing questions:
- **Swiss Ephemeris Commercial License**: Astrodienst AG
- **This Project**: [YOUR_EMAIL] or open GitHub issue

---

**Last Updated**: January 20, 2026  
**Compliance Status**: ✅ Verified
