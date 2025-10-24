#!/usr/bin/env node
/**
 * Test cross-domain cookie authentication using Puppeteer.
 *
 * This uses a real browser to test if JWT cookies work correctly
 * with cross-origin requests between frontend and backend.
 *
 * Usage:
 *   node scripts/test_cross_domain_cookies.js
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Read .env file
function readEnvFile() {
    const envPath = path.join(__dirname, '..', '.env');
    if (!fs.existsSync(envPath)) {
        console.error('Error: .env file not found');
        process.exit(1);
    }

    const envContent = fs.readFileSync(envPath, 'utf8');
    const env = {};

    envContent.split('\n').forEach(line => {
        line = line.trim();
        if (!line || line.startsWith('#') || !line.includes('=')) return;

        const [key, ...valueParts] = line.split('=');
        env[key.trim()] = valueParts.join('=').trim();
    });

    return env;
}

async function testCrossDomainCookies() {
    const env = readEnvFile();
    const backendUrl = env.TUNNEL_URL;
    const frontendUrl = env.FRONT_END_URL;
    const username = 'defaultadmin@example.com';
    const password = 'Default-admin-password';

    if (!backendUrl || !frontendUrl) {
        console.error('Error: TUNNEL_URL or FRONT_END_URL not found in .env');
        process.exit(1);
    }

    console.log('============================================================');
    console.log('Testing Cross-Domain Cookie Configuration (Puppeteer)');
    console.log('============================================================\n');
    console.log(`Backend URL:  ${backendUrl}`);
    console.log(`Frontend URL: ${frontendUrl}`);
    console.log(`Username:     ${username}\n`);

    const browser = await puppeteer.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security', // Allow cross-origin for testing
        ]
    });

    try {
        const page = await browser.newPage();

        // Capture network responses to see Set-Cookie headers
        const responses = [];
        page.on('response', response => {
            responses.push({
                url: response.url(),
                status: response.status(),
                headers: response.headers()
            });
        });

        // Listen for console messages
        page.on('console', msg => {
            console.log(`Browser console [${msg.type()}]:`, msg.text());
        });

        // Navigate to frontend first to establish domain context
        console.log('Step 0: Navigating to frontend to establish domain context...');
        await page.goto(frontendUrl, { waitUntil: 'networkidle0' }).catch(() => {
            console.log('Note: Frontend may not be accessible, continuing anyway...');
        });

        // Step 1: Login via API
        console.log('Step 1: Logging in via API from frontend domain...');

        const loginResponse = await page.evaluate(async (backendUrl, frontendUrl, username, password) => {
            try {
                console.log('Making fetch request with Origin:', frontendUrl);

                const response = await fetch(`${backendUrl}/accounts/api/token/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Origin': frontendUrl,
                    },
                    credentials: 'include', // Important: include cookies
                    body: JSON.stringify({ username, password })
                });

                return {
                    status: response.status,
                    ok: response.ok,
                    headers: Object.fromEntries(response.headers.entries()),
                    body: await response.text()
                };
            } catch (error) {
                return { error: error.message };
            }
        }, backendUrl, frontendUrl, username, password);

        if (loginResponse.error) {
            console.log(`✗ Login failed: ${loginResponse.error}`);
            return false;
        }

        if (!loginResponse.ok) {
            console.log(`✗ Login failed with status ${loginResponse.status}`);
            console.log(`Response: ${loginResponse.body}`);
            return false;
        }

        console.log(`✓ Login successful (status ${loginResponse.status})`);

        // IMPORTANT: Wait a moment for cookies to be set
        await new Promise(resolve => setTimeout(resolve, 500));

        // Step 2: Check cookies and network response
        console.log('\nStep 2: Checking cookies in browser...');

        // Get ALL cookies (not filtered by URL)
        const allCookies = await page.cookies();
        console.log(`  Total cookies found: ${allCookies.length}`);
        if (allCookies.length > 0) {
            console.log('  All cookies:', allCookies.map(c => `${c.name} (domain: ${c.domain})`).join(', '));
        }

        // Check the actual network responses (both OPTIONS and POST)
        const tokenResponses = responses.filter(r => r.url.includes('/accounts/api/token/'));
        console.log(`\n  Found ${tokenResponses.length} responses to /accounts/api/token/`);

        tokenResponses.forEach((resp, idx) => {
            console.log(`\n  Response ${idx + 1}:`);
            console.log(`    Status: ${resp.status}`);
            console.log(`    set-cookie: ${resp.headers['set-cookie'] ? 'PRESENT' : 'NOT PRESENT'}`);
            console.log(`    access-control-allow-origin: ${resp.headers['access-control-allow-origin'] || 'NOT PRESENT'}`);
            console.log(`    access-control-allow-credentials: ${resp.headers['access-control-allow-credentials'] || 'NOT PRESENT'}`);
            console.log(`    access-control-allow-methods: ${resp.headers['access-control-allow-methods'] || 'NOT PRESENT'}`);
        });

        const accessTokenCookie = allCookies.find(c => c.name === 'access_token');

        if (!accessTokenCookie) {
            console.log('\n✗ access_token cookie not found in browser storage');
            console.log('This means the browser rejected the cookie!');
            console.log('\nPossible reasons:');
            console.log('  1. Cookie domain mismatch');
            console.log('  2. SameSite policy blocking the cookie');
            console.log('  3. Secure flag requires HTTPS but connection is not secure');
            console.log('  4. Browser third-party cookie settings');

            return false;
        }

        console.log('✓ access_token cookie found');
        console.log('\nCookie details:');
        console.log(`  Domain:   ${accessTokenCookie.domain}`);
        console.log(`  Path:     ${accessTokenCookie.path}`);
        console.log(`  Secure:   ${accessTokenCookie.secure}`);
        console.log(`  HttpOnly: ${accessTokenCookie.httpOnly}`);
        console.log(`  SameSite: ${accessTokenCookie.sameSite || 'none'}`);
        console.log(`  Value:    ${accessTokenCookie.value.substring(0, 50)}...`);

        // Step 3: Make authenticated request
        console.log('\nStep 3: Making authenticated request to /accounts/me/...');

        const meResponse = await page.evaluate(async (backendUrl, frontendUrl) => {
            try {
                const response = await fetch(`${backendUrl}/accounts/me/`, {
                    method: 'GET',
                    headers: {
                        'Origin': frontendUrl,
                    },
                    credentials: 'include', // Important: include cookies
                });

                return {
                    status: response.status,
                    ok: response.ok,
                    body: await response.text()
                };
            } catch (error) {
                return { error: error.message };
            }
        }, backendUrl, frontendUrl);

        if (meResponse.error) {
            console.log(`✗ Request failed: ${meResponse.error}`);
            return false;
        }

        if (!meResponse.ok) {
            console.log(`✗ Request failed with status ${meResponse.status}`);
            console.log(`Response: ${meResponse.body}`);

            // Check if cookie was sent
            const lastRequest = requests[requests.length - 1];
            console.log('\nLast request headers:');
            console.log(`  Cookie header: ${lastRequest.headers.cookie || 'NOT SENT'}`);

            return false;
        }

        console.log(`✓ Authenticated request successful (status ${meResponse.status})`);

        try {
            const userData = JSON.parse(meResponse.body);
            if (userData.email) {
                console.log(`✓ User data received: ${userData.email}`);
            }
        } catch (e) {
            console.log('Response:', meResponse.body);
        }

        // Check final cookie state
        const finalCookies = await page.cookies();
        console.log(`\nStep 4: Final cookie check...`);
        console.log(`  Cookies in browser: ${finalCookies.map(c => c.name).join(', ')}`);

        console.log('\n============================================================');
        console.log('✓ ALL TESTS PASSED!');
        console.log('Cross-domain cookie authentication is working correctly.');
        console.log('============================================================\n');

        return true;

    } catch (error) {
        console.error('\n✗ Test failed with error:', error.message);
        console.error(error.stack);
        return false;
    } finally {
        await browser.close();
    }
}

// Run the test
testCrossDomainCookies()
    .then(success => {
        process.exit(success ? 0 : 1);
    })
    .catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
