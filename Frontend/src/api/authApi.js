import { supabase } from '../lib/supabase';

/**
 * Login user with email and password
 * @param {string} email - User's email
 * @param {string} password - User's password
 * @returns {Promise<{success: boolean, data?: object, error?: string}>}
 */
export const loginUser = async (email, password) => {
  try {
    const { data, error } = await supabase
      .from('users_voice')
      .select('*')
      .eq('email_address', email)
      .eq('password', password)
      .single();

    if (error || !data) {
      return {
        success: false,
        error: 'Invalid email or password',
      };
    }

    return {
      success: true,
      data: {
        user_id: data.user_id,
        email: data.email_address,
        name: data.name,
      },
    };
  } catch (error) {
    console.error('Login error:', error);
    return {
      success: false,
      error: 'An error occurred during login',
    };
  }
};

/**
 * Register a new user
 * @param {string} email - User's email
 * @param {string} name - User's name
 * @param {string} password - User's password
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export const registerUser = async (email, name, password) => {
  try {
    // Check if user already exists
    const { data: existingUser } = await supabase
      .from('users_voice')
      .select('email_address')
      .eq('email_address', email)
      .single();

    if (existingUser) {
      return {
        success: false,
        error: 'Email already registered',
      };
    }

    // Insert new user
    const { error } = await supabase
      .from('users_voice')
      .insert([
        {
          email_address: email,
          name: name,
          password: password,
        },
      ]);

    if (error) {
      console.error('Registration error:', error);
      return {
        success: false,
        error: 'Registration failed. Please try again.',
      };
    }

    return {
      success: true,
    };
  } catch (error) {
    console.error('Registration error:', error);
    return {
      success: false,
      error: 'An error occurred during registration',
    };
  }
};

/**
 * Check if user exists
 * @param {string} email - User's email
 * @returns {Promise<{exists: boolean}>}
 */
export const checkUserExists = async (email) => {
  try {
    const { data } = await supabase
      .from('users_voice')
      .select('email_address')
      .eq('email_address', email)
      .single();

    return {
      exists: !!data,
    };
  } catch (error) {
    console.error('Error checking user:', error);
    return {
      exists: false,
    };
  }
};
