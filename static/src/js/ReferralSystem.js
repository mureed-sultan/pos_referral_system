/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// ------------------------------------------------------
// PosOrder Patch
// ------------------------------------------------------
patch(PosOrder.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON();
        if (this.uiState.referralData) {
            json.referral_data = this.uiState.referralData;
        }
        return json;
    },

    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        console.log(this.uiState)
        console.log(result)
        if (this.uiState.referralData) {
            result.receipt_referral_data = this.uiState.referralData;
            console.log("✅ EXPORTING REFERRAL DATA TO RECEIPT:", result.receipt_referral_data);
        }
        return result;
    },

    setReferralData(data) {
        this.uiState.referralData = data;
    },

    getReferralData() {
        return this.uiState.referralData || null;
    },
});

// ------------------------------------------------------
// Referral Popup Component
// ------------------------------------------------------
class ReferralPopup extends Component {
    static template = "pos_referral_system.ReferralPopup";
    static props = {
        close: Function,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({
            action: "generate",
            code: "",
            error: "",
            generatedCode: "",
        });
    }

    get selectedCustomer() {
        const order = this.pos.get_order();
        return order ? order.get_partner() : null;
    }

    get hasPhoneNumber() {
        return this.selectedCustomer && (this.selectedCustomer.phone || this.selectedCustomer.mobile);
    }

    get currentPosConfigId() {
        return this.pos.config && this.pos.config.id;
    }

    async generateCode() {
        const customer = this.selectedCustomer;
        if (!customer) {
            this.state.error = "Please select a customer first.";
            return;
        }

        if (!this.hasPhoneNumber) {
            this.state.error = "Customer must have a phone number to generate referral code.";
            return;
        }

        if (!this.currentPosConfigId) {
            this.state.error = "No POS configuration found.";
            return;
        }

        try {
            const phone = customer.phone || customer.mobile;
            const customerName = customer.name || "CUST";

            const result = await this.orm.call(
                "pos.order",
                "create_referral_code",
                [customer.id, phone, false, this.currentPosConfigId, customerName]
            );

            if (result) {
                const code = result.code;
                const referralId = result.referral_id;
                const order = this.pos.get_order();
                if (order) {
                    order.setReferralData({
                        generated_code: code,
                        referral_id: referralId,
                        customer_name: customer.name,
                    });
                }
                this.state.generatedCode = code;
                this.state.error = "";
                this.showNotification(`Referral code generated: ${code}`, 'success');
            }
        } catch (error) {
            console.error("Error generating referral code:", error);
            this.state.error = error.message || "Failed to generate referral code. Please try again.";
        }
    }

   async redeemCode() {
    if (!this.state.code.trim()) {
        this.state.error = "Please enter a referral code.";
        return;
    }

    try {
        const order = this.pos.get_order();
        if (!order) {
            this.state.error = "No active order found.";
            return;
        }

        const orderAmount = order.get_total_with_tax();
        const referralCode = this.state.code.trim().toUpperCase();
        const result = await this.orm.call(
            "pos.order",
            "apply_referral_discount",
            [referralCode, orderAmount, this.currentPosConfigId]
        );

        if (result.success) {
            const discountAmount = result.discount_amount;

            // Apply discount using the direct method
            const success = await this.applyDirectDiscount(order, discountAmount, referralCode);

            if (success) {
                this.state.error = "";
                this.props.close();
                this.showNotification(`Referral discount of ${discountAmount.toFixed(2)} AED applied!`, 'success');
            } else {
                this.showNotification(`Referral recorded but discount not applied. Manual adjustment needed.`, 'warning');
            }

        } else {
            this.state.error = result.message;
        }
    } catch (error) {
        console.error("Error applying referral code:", error);
        this.state.error = error.message || "Failed to apply referral code.";
    }
}

    async applyDirectDiscount(order, discountAmount, referralCode) {

    const orderLines = order.get_orderlines();
    // Apply discount regardless
    const orderTotal = order.get_total_with_tax();
    const discountPercentage = (discountAmount / orderTotal) * 100;


    orderLines.forEach((line, index) => {
        line.discount = discountPercentage;
    });

    order.setReferralData({
        used_code: referralCode,
        discount_amount: discountAmount,
    });

    return true;
}

// Helper method to get all available products
getAllAvailableProducts() {
    try {
        // Try different methods to access products
        if (this.pos.db.product_by_id) {
            return Object.values(this.pos.db.product_by_id);
        }

        // Alternative access methods
        if (this.pos.db._products) {
            return Object.values(this.pos.db._products);
        }

        // Last resort - try to get from categories
        if (this.pos.db.get_category_ids && this.pos.db.get_product_by_category_id) {
            const categoryIds = this.pos.db.get_category_ids();
            let allProducts = [];
            categoryIds.forEach(categoryId => {
                const categoryProducts = this.pos.db.get_product_by_category_id(categoryId);
                if (categoryProducts) {
                    allProducts = allProducts.concat(categoryProducts);
                }
            });
            return allProducts;
        }

        return [];
    } catch (error) {
        console.error("Error getting products:", error);
        return [];
    }
}

// Helper method to save referral data
//saveReferralData(order, discountAmount, referralCode) {
//    order.setReferralData({
//        used_code: referralCode,
//        discount_amount: discountAmount,
//        discount_percentage: (discountAmount / order.get_total_with_tax()) * 100,
//        customer_name: order.get_partner() ? order.get_partner().name : "Customer",
//    });
//}

// Add this helper method to find discount product
getDiscountProduct() {
    try {
        // Method 1: Use configured discount product
        if (this.pos.config.discount_product_id && this.pos.config.discount_product_id[0]) {
            const discountProduct = this.pos.db.get_product_by_id(this.pos.config.discount_product_id[0]);
            if (discountProduct) return discountProduct;
        }

        // Method 2: Find any discount product by name
        const allProducts = Object.values(this.pos.db.product_by_id || {});
        const discountProduct = allProducts.find(product =>
            product.display_name && product.display_name.toLowerCase().includes('discount')
        );

        return discountProduct || null;

    } catch (error) {
        console.error("Error finding discount product:", error);
        return null;
    }
}

    addDiscountProductToOrder(order, discountProduct, discountAmount, referralCode) {
        try {
            // Use the standard POS method to add product
            const discountLine = order.add_product(discountProduct, {
                price: -Math.abs(discountAmount), // Negative price for discount
                quantity: 1,
                merge: false
            });

            if (discountLine) {

                // Ensure the price stays negative
                if (discountLine.set_unit_price) {
                    discountLine.set_unit_price(-Math.abs(discountAmount));
                } else {
                    discountLine.price = -Math.abs(discountAmount);
                }

                discountLine.quantity = 1;

                // Add referral note
                if (discountLine.set_note) {
                    discountLine.set_note(`Referral: ${referralCode}`);
                } else if (discountLine.note !== undefined) {
                    discountLine.note = `Referral: ${referralCode}`;
                }

                // Force order recalculation
                order.trigger('change');

                const newTotal = order.get_total_with_tax();

                return true;
            } else {
                console.error("❌ Failed to create discount line");
                return false;
            }
        } catch (error) {
            console.error("❌ Error adding discount product:", error);
            return false;
        }
    }

    applyManualLineDiscount(order, discountAmount, referralCode) {
        try {

            const originalTotal = order.get_total_with_tax();
            if (originalTotal <= 0 || !order.orderlines || order.orderlines.length === 0) {
                console.warn("⚠️ No order lines to apply discount to");
                return false;
            }

            const discountPercentage = (discountAmount / originalTotal) * 100;

            // Apply discount proportionally to each line
            order.orderlines.forEach((line, index) => {
                if (line.product && !line.is_program_reward) {
                    const lineValue = line.get_display_price() * line.quantity;
                    const lineDiscount = (lineValue * discountPercentage) / 100;

                    // Add to existing discount
                    const currentDiscount = line.discount || 0;
                    line.discount = currentDiscount + lineDiscount;

                }
            });

            // Trigger order update
            order.trigger('change');

            const newTotal = order.get_total_with_tax();
            const actualDiscount = originalTotal - newTotal;
            return Math.abs(actualDiscount - discountAmount) < 0.01;
        } catch (error) {
            console.error("❌ Manual line discount failed:", error);
            return false;
        }
    }

    showNotification(message, type = 'success') {
        try {
            if (this.pos.ui && this.pos.ui.notification) {
                this.pos.ui.notification(message, type);
            } else if (this.pos.notification) {
                this.pos.notification(message, type);
            } else if (this.env.services && this.env.services.notification) {
                this.env.services.notification.add(message, { type: type });
            } else {
            }
        } catch (error) {
            console.error(`[${type.toUpperCase()}] ${message}`);
        }
    }

    close() {
        this.props.close();
    }
}

// ------------------------------------------------------
// Referral Button Component
// ------------------------------------------------------
class ReferralButton extends Component {
    static template = "pos_referral_system.ReferralButton";
    static props = {};

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.pos = usePos();
    }

    onClick() {
        const order = this.pos.get_order();
        if (!order) {
            console.warn("[ReferralButton] No order found, cannot open popup.");
            this.showNotification("Please start an order first.", 'warning');
            return;
        }

        try {
            this.dialog.add(ReferralPopup, {
                close: () => {
                    this.dialog.close();
                },
            });
        } catch (error) {
            console.error("[ReferralButton] Error opening dialog:", error);
        }
    }

    showNotification(message, type = 'success') {
        try {
            if (this.pos.ui && this.pos.ui.notification) {
                this.pos.ui.notification(message, type);
            } else if (this.pos.notification) {
                this.pos.notification(message, type);
            } else if (this.env.services && this.env.services.notification) {
                this.env.services.notification.add(message, { type: type });
            } else {
                console.log(`[${type.toUpperCase()}] ${message}`);
            }
        } catch (error) {
            console.error(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// ------------------------------------------------------
// ControlButtons Patch
// ------------------------------------------------------
patch(ControlButtons, {
    components: { ...ControlButtons.components, ReferralButton },
});

export { ReferralButton, ReferralPopup };