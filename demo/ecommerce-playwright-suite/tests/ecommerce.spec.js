const { test, expect } = require('@playwright/test');

test.describe('E-Commerce QA Automation Regression Suite (SauceDemo)', () => {

  test('TC-101: User Authentication & Product Catalog Render', async ({ page }) => {
    // 1. Navigate to store
    await page.goto('/');
    await expect(page).toHaveTitle(/Swag Labs/);

    // 2. Perform standard login
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    // 3. Verify successful redirection and product catalog
    await expect(page).toHaveURL(/.*inventory.html/);
    const inventoryItems = page.locator('.inventory_item');
    await expect(inventoryItems).toHaveCount(6);

    // Pause briefly so the user sees the inventory on their screen
    await page.waitForTimeout(1500);

    // 4. Capture milestone screenshot
    await page.screenshot({ path: 'test-results/tc101_catalog.png' });
  });

  test('TC-102: Product Catalog Sorting & Shopping Cart Badge', async ({ page }) => {
    // Pre-condition: Login
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    // 1. Sort products: Price (low to high)
    const sortDropdown = page.locator('[data-test="product-sort-container"]');
    await sortDropdown.selectOption('lohi');

    // 2. Assert first item is the lowest price item ($7.99)
    const firstItemPrice = page.locator('.inventory_item_price').first();
    await expect(firstItemPrice).toHaveText('$7.99');

    // 3. Add top two items to cart
    await page.locator('.inventory_item').nth(0).locator('button').click();
    await page.locator('.inventory_item').nth(1).locator('button').click();

    // 4. Verify shopping cart badge increments to 2
    const cartBadge = page.locator('.shopping_cart_badge');
    await expect(cartBadge).toHaveText('2');
  });

  test('TC-103: Full 3-Step Checkout Journey with Tax Calculation', async ({ page }) => {
    // Pre-condition: Login
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('standard_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    // 1. Add backpack ($29.99) to cart
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();

    // 2. Navigate to cart and proceed to checkout
    await page.locator('.shopping_cart_link').click();
    await expect(page).toHaveURL(/.*cart.html/);
    await page.locator('[data-test="checkout"]').click();

    // 3. Step 1: Fill shipping address information
    await expect(page).toHaveURL(/.*checkout-step-one.html/);
    await page.locator('[data-test="firstName"]').fill('Naga');
    await page.locator('[data-test="lastName"]').fill('QA');
    await page.locator('[data-test="postalCode"]').fill('94043');
    await page.locator('[data-test="continue"]').click();

    // 4. Step 2: Overview & Pricing assertions
    await expect(page).toHaveURL(/.*checkout-step-two.html/);
    await expect(page.locator('.summary_subtotal_label')).toHaveText('Item total: $29.99');
    await expect(page.locator('.summary_tax_label')).toHaveText('Tax: $2.40');
    await expect(page.locator('.summary_total_label')).toHaveText('Total: $32.39');

    // 5. Complete order
    await page.locator('[data-test="finish"]').click();
    await expect(page).toHaveURL(/.*checkout-complete.html/);
    const completeHeader = page.locator('.complete-header');
    await expect(completeHeader).toHaveText('Thank you for your order!');
  });

  test('TC-104: Locked-Out User Security Boundary', async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-test="username"]').fill('locked_out_user');
    await page.locator('[data-test="password"]').fill('secret_sauce');
    await page.locator('[data-test="login-button"]').click();

    // Verify error banner is visible and has correct message
    const errorMsg = page.locator('[data-test="error"]');
    await expect(errorMsg).toBeVisible();
    await expect(errorMsg).toContainText('Sorry, this user has been locked out.');
    
    // Pause briefly so user can see error banner on UI
    await page.waitForTimeout(1500);

    // Capture screenshot of locked-out banner
    await page.screenshot({ path: 'test-results/tc104_locked_out.png' });
  });

  test.skip('TC-105: International Duty & Customs Currency Conversion', async () => {
    // Feature flag disabled for v1.0 release - marks test as SKIPPED
  });

});
